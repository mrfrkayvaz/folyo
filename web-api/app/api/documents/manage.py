"""Belge yönetimi: chunk görüntüleme, durum, iptal, silme (worker iş kontrolü dahil)."""

import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select as sm_select

from shared.core import fs as core_fs
from ...core.database import get_factory
from shared.core.enums import DocumentStatus
from shared.core.logging import get_logger
from shared.models import Document, DocumentQuestion, EmbeddingJob
from shared.services import chroma_store
from ...services import jobs
from ...services.jobs import storage_dir

router = APIRouter()
LOG = get_logger("api.documents.manage")


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
    await jobs.schedule_workspace_summary(ws_id)
    return {"deleted": True}