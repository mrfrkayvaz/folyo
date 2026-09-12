import asyncio
import urllib.parse
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlmodel import select as sm_select

from ..core import fs as core_fs
from ..core.constants import MAX_UPLOAD_SIZE
from ..core.database import get_factory
from ..core.enums import DocumentStatus
from ..core.logging import get_logger
from ..models import Document, DocumentQuestion, EmbeddingJob, Workspace
from ..services import chroma_store, jobs, upload
from ..services.extract.constants import SUPPORTED_EXTS
from ..services.jobs import storage_dir

router = APIRouter(prefix="/api", tags=["documents"])
LOG = get_logger("api.documents")


def _spawn_embed_job(workspace_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> None:
    """Embed görevini arka planda başlatır; hataları uvicorn logger'ına yazar.

    `asyncio.create_task` fire-and-forget'tır — done-callback olmadan görev hataları
    sessizce yutulurdu (dbg'de görünmezdi). Bu sarıcı başarısızlığı traceback ile loglar.
    """
    task = asyncio.create_task(jobs.run_embed_job(workspace_id, document_id, filename))

    def _log_result(t: asyncio.Task) -> None:
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            LOG.error(
                "[embed-job] belge %s embed görevi başarısız",
                document_id,
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    task.add_done_callback(_log_result)


@router.get("/chunks")
async def get_chunks(ids: str):
    """`doc_id:chunk_index` kimlikleriyle chunk içeriklerini döndürür (InspectModal).

    Örn: `?ids=e603…:3,e603…:4` — en fazla 20 kimlik, virgülle ayrılmış.
    """
    parts = [p.strip() for p in ids.split(",") if p.strip()]
    if not parts or len(parts) > 20:
        raise HTTPException(422, "ids: virgülle ayrılmış 1-20 'doc_id:chunk_index' beklenir.")
    rows = await chroma_store.get_chunks_by_ids(parts)
    return {
        "chunks": [
            {
                "id": f"{r['doc_id']}:{r['chunk_index']}",
                "doc_id": r["doc_id"],
                "chunk_index": r["chunk_index"],
                "page_number": r["page_number"],
                "content_type": r["content_type"],
                "page_context": r.get("page_context", ""),
                "breadcrumbs": r.get("breadcrumbs", []),
                "section_title": r.get("section_title", ""),
                "image_path": r.get("image_path", ""),
                "name": r["name"],
                "text": r["text"],
            }
            for r in rows
        ],
        "found": len(rows),
    }


@router.post("/workspaces/{wid}/documents")
async def upload_document(wid: uuid.UUID, request: Request):
    filename = urllib.parse.unquote(request.headers.get("X-Filename", "belge"))
    filename = Path(filename).name
    try:
        size = int(request.query_params.get("size") or 0)
    except ValueError:
        size = 0

    # Ön-doğrulama: gövde akışı BAŞLAMADAN önce uzantı ve boyut kontrolü.
    file_ext = Path(filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTS:
        allowed = ", ".join(sorted(SUPPORTED_EXTS))
        raise HTTPException(
            415,
            detail=f"Desteklenmeyen dosya türü '{file_ext or '(uzantı yok)'}'. "
            f"Desteklenen dosyalar: {allowed}.",
        )
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Dosya çok büyük (limit: 25 MB).")

    file_type = file_ext.lstrip(".")

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
    result = await upload.stream_to_disk(request, path, size)

    if result.aborted or result.incomplete:
        async with get_factory()() as s:
            d = await s.get(Document, doc.id)
            if d:
                d.status = DocumentStatus.cancelled
                d.updated_at = d.updated_at.__class__.now()
                s.add(d)
                await s.commit()
        await core_fs.rmtree_ignore(ddir)
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

    _spawn_embed_job(wid, doc.id, doc.filename)
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
        "summary_status": d.summary_status,
        "summary_error": d.summary_error,
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
        await core_fs.rmtree_ignore(storage_dir(did))
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
    await core_fs.rmtree_ignore(storage_dir(did))
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


@router.get("/documents/{did}/crops/{name}")
async def get_crop(did: uuid.UUID, name: str):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
    p = storage_dir(did) / "crops" / Path(name).name
    if not p.exists():
        raise HTTPException(404, "Kırpım bulunamadı.")
    return FileResponse(p)
