"""Contextus Web API — workspace'li belge analiz & soru-cevap (RAG, stream).

Uçlar:
  workspaces : POST (yeni sohbet) · GET liste · GET/{id} (mesajlar) · DELETE/{id} (cascade)
  documents  : POST /workspaces/{wid}/documents (stream + X-Filename) · GET liste
               GET/DELETE /documents/{id} · POST cancel · GET file
  qa         : POST /workspaces/{wid}/qa  (SSE: meta→delta*→done; mesajlar kaydedilir)

Veritabanı: Postgres (SQLModel) — dosya deposit: storage/<doc_id>/ — vektörler: ChromaDB.
"""

import asyncio
import json
import shutil
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlmodel import select as sm_select

from . import db as db_mod
from .config import get_settings
from .models import ChatMessage, ChatRole, Document, DocumentStatus, EmbeddingJob, EmbeddingStatus, Workspace
from .services import chroma_store, jobs
from .services.rag import qa_events

MAX_UPLOAD = 25 * 1024 * 1024  # 25 MB


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await db_mod.init_db()  # tablolar + stale işleri failed yap
    yield


app = FastAPI(
    title="Contextus API",
    description="Belge Analiz ve Soru-Cevap (workspace'li, streaming RAG)",
    version="0.3.0",
    lifespan=lifespan,
)


class QaBody(BaseModel):
    question: str


class WorkspaceBody(BaseModel):
    name: str | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream(gen):
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _storage_dir(doc_id: uuid.UUID) -> Path:
    return Path(get_settings().storage_dir) / str(doc_id)


# ── Sağlık ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    try:
        async with db_mod.get_factory()() as s:
            ws = (await s.execute(select(Workspace))).scalars().all()
            docs = (await s.execute(select(Document))).scalars().all()
            msgs = (await s.execute(select(ChatMessage))).scalars().all()
        return {"status": "ok", "workspaces": len(ws), "documents": len(docs), "messages": len(msgs)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


# ── Workspaces (sohbetler) ────────────────────────────────────────────────────


@app.post("/api/workspaces")
async def create_workspace(body: WorkspaceBody | None = None):
    name = (body.name if body else None) or "Yeni sohbet"
    ws = Workspace(name=name)
    async with db_mod.get_factory()() as s:
        s.add(ws)
        await s.commit()
        await s.refresh(ws)
    return {"id": str(ws.id), "name": ws.name, "created_at": ws.created_at.isoformat()}


@app.get("/api/workspaces")
async def list_workspaces():
    async with db_mod.get_factory()() as s:
        rows = (await s.execute(sm_select(Workspace).order_by(Workspace.created_at.desc()))).scalars().all()
        out = []
        for ws in rows:
            last = (
                await s.execute(
                    sm_select(ChatMessage.created_at)
                    .where(ChatMessage.workspace_id == ws.id)
                    .order_by(ChatMessage.created_at.desc())
                    .limit(1)
                )
            ).scalar()
            out.append(
                {
                    "id": str(ws.id),
                    "name": ws.name,
                    "created_at": ws.created_at.isoformat(),
                    "last_message_at": last.isoformat() if last else None,
                }
            )
    return {"workspaces": out}


@app.get("/api/workspaces/{wid}")
async def get_workspace(wid: uuid.UUID):
    async with db_mod.get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        msgs = (
            await s.execute(
                sm_select(ChatMessage)
                .where(ChatMessage.workspace_id == wid)
                .order_by(ChatMessage.created_at.asc())
            )
        ).scalars().all()
        docs = (await s.execute(sm_select(Document).where(Document.workspace_id == wid))).scalars().all()
    return {
        "workspace": {"id": str(ws.id), "name": ws.name, "created_at": ws.created_at.isoformat()},
        "messages": [
            {
                "id": str(m.id),
                "role": m.role.value,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
        "documents": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "size": d.size,
                "status": d.status.value,
                "chunk_count": d.chunk_count,
                "error": d.error,
            }
            for d in docs
        ],
    }


@app.delete("/api/workspaces/{wid}")
async def delete_workspace(wid: uuid.UUID):
    async with db_mod.get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        docs = list((await s.execute(sm_select(Document).where(Document.workspace_id == wid))).scalars())
        for d in docs:
            shutil.rmtree(_storage_dir(d.id), ignore_errors=True)
        await s.delete(ws)  # documents/messages/embeddings CASCADE
        await s.commit()
    await chroma_store.delete_workspace(wid)
    return {"deleted": True}


# ── Documents (belge yükleme/dizinleme) ───────────────────────────────────────


@app.post("/api/workspaces/{wid}/documents")
async def upload_document(wid: uuid.UUID, request: Request):
    settings = get_settings()
    filename = urllib.parse.unquote(request.headers.get("X-Filename", "belge"))
    filename = Path(filename).name  # yol kaçışlarını temizle
    try:
        size = int(request.query_params.get("size") or 0)
    except ValueError:
        size = 0
    if size > MAX_UPLOAD:
        raise HTTPException(413, "Dosya çok büyük (limit: 25 MB).")
    file_type = Path(filename).suffix.lower().lstrip(".") or "bin"

    # workspace var mı?
    async with db_mod.get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        doc = Document(workspace_id=wid, filename=filename, file_type=file_type, size=size)
        s.add(doc)
        await s.commit()
        await s.refresh(doc)

    # stream ile depola (istemci iptal ederse kısa okuma → cancelled)
    ddir = _storage_dir(doc.id)
    ddir.mkdir(parents=True, exist_ok=True)
    path = ddir / filename
    received = 0
    aborted = False
    try:
        with open(path, "wb") as f:
            async for chunk in request.stream():
                f.write(chunk)
                received += len(chunk)
                if size and received > size:
                    aborted = True
                    break
    except Exception:
        aborted = True
    incomplete = size and received < size

    if aborted or incomplete:
        async with db_mod.get_factory()() as s:
            d = await s.get(Document, doc.id)
            d.status = DocumentStatus.cancelled
            d.updated_at = d.updated_at.__class__.now()
            s.add(d)
            await s.commit()
        shutil.rmtree(ddir, ignore_errors=True)
        return {"id": str(doc.id), "filename": filename, "status": "cancelled"}

    # embed görevi başlat
    async with db_mod.get_factory()() as s:
        d = await s.get(Document, doc.id)
        d.status = DocumentStatus.pending
        d.updated_at = d.updated_at.__class__.now()
        s.add(d)
        job = EmbeddingJob(id=doc.id, document_id=doc.id)
        s.add(job)
        await s.commit()

    asyncio.create_task(jobs.run_embed_job(wid, doc.id, doc.filename))
    return {"id": str(doc.id), "filename": filename, "status": "pending"}


@app.get("/api/documents/{did}")
async def document_status(did: uuid.UUID):
    async with db_mod.get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        job = await s.get(EmbeddingJob, did)
    return {
        "id": str(d.id),
        "filename": d.filename,
        "status": d.status.value,
        "chunk_count": d.chunk_count,
        "error": d.error,
        "embed": {
            "status": job.status.value if job else None,
            "chunks": job.chunks if job else None,
            "dim": job.dim if job else None,
            "progress": job.progress if job else 0,
        },
    }


@app.post("/api/documents/{did}/cancel")
async def cancel_document(did: uuid.UUID):
    async with db_mod.get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        status = d.status.value
    if status in ("embedded", "failed", "cancelled"):
        raise HTTPException(409, f"İptal edilemez (durum: {status}).")
    if status == "uploading":
        async with db_mod.get_factory()() as s:
            d = await s.get(Document, did)
            d.status = DocumentStatus.cancelled
            d.updated_at = d.updated_at.__class__.now()
            s.add(d)
            await s.commit()
        shutil.rmtree(_storage_dir(did), ignore_errors=True)
        return {"cancelled": True, "status": "cancelled"}
    # pending/embedding → görev bir sonraki batch'te durur ve temizler
    jobs.request_cancel(str(did))
    return {"cancelled": True, "status": "cancelling"}


@app.delete("/api/documents/{did}")
async def delete_document(did: uuid.UUID):
    async with db_mod.get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        await s.delete(d)  # embeddings CASCADE
        await s.commit()
    shutil.rmtree(_storage_dir(did), ignore_errors=True)
    await chroma_store.delete_document(did)
    return {"deleted": True}


@app.get("/api/documents/{did}/file")
async def download_document(did: uuid.UUID):
    async with db_mod.get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
    p = _storage_dir(did) / d.filename
    if not p.exists():
        raise HTTPException(404, "Dosya depoda yok.")
    return FileResponse(p, filename=d.filename)


# ── Soru-Cevap (workspace-scope'lu, streaming) ────────────────────────────────

_PLACEHOLDER = "Yeni sohbet"


@app.post("/api/workspaces/{wid}/qa")
async def ask(wid: uuid.UUID, body: QaBody):
    question = body.question.strip()
    if not question:
        raise HTTPException(422, "Soru boş olamaz.")

    async with db_mod.get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        # kullanıcı mesajını kaydet
        s.add(ChatMessage(workspace_id=wid, role=ChatRole.user, content=question))
        # ilk mesajsa adı otomatik yaz (ilk 60 karakter)
        if ws.name == _PLACEHOLDER:
            ws.name = " ".join(question.split())[:60]
            s.add(ws)
        await s.commit()

    async def gen():
        sf = db_mod.get_factory()
        acc = ""
        err = None
        sources = None
        try:
            async for ev in qa_events(wid, question):
                yield _sse(ev["type"], {k: v for k, v in ev.items() if k != "type"})
                if ev["type"] == "delta":
                    acc += ev["text"]
                elif ev["type"] == "meta":
                    sources = ev.get("sources")
                elif ev["type"] == "error":
                    err = ev.get("message") or err
                elif ev["type"] == "done":
                    sources = ev.get("sources") or sources
            content = acc if acc else (f"⚠️ {err}" if err else "Yanıt alınırken bir hata oluştu.")
            async with sf() as s:
                s.add(
                    ChatMessage(
                        workspace_id=wid,
                        role=ChatRole.assistant,
                        content=content,
                        citations=sources or None,
                    )
                )
                await s.commit()
        except Exception:
            async with sf() as s:
                s.add(
                    ChatMessage(
                        workspace_id=wid,
                        role=ChatRole.assistant,
                        content="Yanıt alınırken bir hata oluştu.",
                        citations=None,
                    )
                )
                await s.commit()

    return _stream(gen())