import asyncio
import shutil
import urllib.parse
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlmodel import select as sm_select

from ..core.constants import MAX_UPLOAD_SIZE
from ..core.database import get_factory
from ..core.enums import DocumentStatus
from ..models import Document, DocumentQuestion, EmbeddingJob, Workspace
from ..services import chroma_store, jobs
from ..services.jobs import storage_dir

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/workspaces/{wid}/documents")
async def upload_document(wid: uuid.UUID, request: Request):
    filename = urllib.parse.unquote(request.headers.get("X-Filename", "belge"))
    filename = Path(filename).name
    try:
        size = int(request.query_params.get("size") or 0)
    except ValueError:
        size = 0

    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Dosya çok büyük (limit: 25 MB).")

    file_type = Path(filename).suffix.lower().lstrip(".") or "bin"

    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        doc = Document(workspace_id=wid, filename=filename, file_type=file_type, size=size)
        s.add(doc)
        await s.commit()
        await s.refresh(doc)

    ddir = storage_dir(doc.id)
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
        async with get_factory()() as s:
            d = await s.get(Document, doc.id)
            if d:
                d.status = DocumentStatus.cancelled
                d.updated_at = d.updated_at.__class__.now()
                s.add(d)
                await s.commit()
        shutil.rmtree(ddir, ignore_errors=True)
        return {"id": str(doc.id), "filename": filename, "status": "cancelled"}

    async with get_factory()() as s:
        d = await s.get(Document, doc.id)
        if d:
            d.status = DocumentStatus.pending
            d.updated_at = d.updated_at.__class__.now()
            s.add(d)
            job = EmbeddingJob(id=doc.id, document_id=doc.id)
            s.add(job)
            await s.commit()

    asyncio.create_task(jobs.run_embed_job(wid, doc.id, doc.filename))
    return {"id": str(doc.id), "filename": filename, "status": "pending"}


@router.get("/documents/{did}")
async def document_status(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        job = await s.get(EmbeddingJob, did)
        qs = (
            await s.execute(
                sm_select(DocumentQuestion)
                .where(DocumentQuestion.document_id == did)
                .order_by(DocumentQuestion.position)
            )
        ).scalars().all()
    return {
        "id": str(d.id),
        "filename": d.filename,
        "status": d.status.value,
        "chunk_count": d.chunk_count,
        "error": d.error,
        "summary": d.summary,
        "stats": d.stats,
        "starter_questions": [q.question for q in qs],
        "embed": {
            "status": job.status.value if job else None,
            "chunks": job.chunks if job else None,
            "dim": job.dim if job else None,
            "progress": job.progress if job else 0,
        },
    }


@router.post("/documents/{did}/cancel")
async def cancel_document(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        status = d.status.value

    if status in ("embedded", "failed", "cancelled"):
        raise HTTPException(409, f"İptal edilemez (durum: {status}).")

    if status == "uploading":
        async with get_factory()() as s:
            d = await s.get(Document, did)
            if d:
                d.status = DocumentStatus.cancelled
                d.updated_at = d.updated_at.__class__.now()
                s.add(d)
                await s.commit()
        shutil.rmtree(storage_dir(did), ignore_errors=True)
        return {"cancelled": True, "status": "cancelled"}

    jobs.request_cancel(str(did))
    return {"cancelled": True, "status": "cancelling"}


@router.delete("/documents/{did}")
async def delete_document(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        ws_id = d.workspace_id
        await s.delete(d)
        await s.commit()
    jobs.request_cancel(str(did))
    shutil.rmtree(storage_dir(did), ignore_errors=True)
    await chroma_store.delete_document(did)
    jobs.schedule_workspace_summary(ws_id)
    return {"deleted": True}


@router.get("/documents/{did}/file")
async def download_document(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
    p = storage_dir(did) / d.filename
    if not p.exists():
        raise HTTPException(404, "Dosya depoda yok.")
    return FileResponse(p, filename=d.filename)
