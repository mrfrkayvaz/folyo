import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..core.database import get_factory
from ..models import Document, DocumentQuestion, EmbeddingJob
from ..services.chunks import chunks_for

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/{did}")
async def get_document(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        job = await s.get(EmbeddingJob, did)
        qs = (
            await s.execute(
                select(DocumentQuestion)
                .where(DocumentQuestion.document_id == did)
                .order_by(DocumentQuestion.position)
            )
        ).scalars().all()

    chunks = chunks_for(str(did))
    return {
        "document": {
            "id": str(d.id),
            "workspace_id": str(d.workspace_id),
            "filename": d.filename,
            "file_type": d.file_type,
            "size": d.size,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "error": d.error,
            "summary": d.summary,
            "summary_status": d.summary_status,
            "summary_error": d.summary_error,
            "questions": [q.question for q in qs],
            "stats": d.stats,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "process": {
                "status": d.status,
                "error": d.error,
                "summary_status": d.summary_status,
                "summary_error": d.summary_error,
                "job": {
                    "status": job.status if job else None,
                    "chunks": job.chunks if job else None,
                    "dim": job.dim if job else None,
                    "progress": job.progress if job else 0,
                    "error": job.error if job else None,
                    "created_at": job.created_at.isoformat() if job and job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job and job.updated_at else None,
                },
            },
        },
        "chunks": chunks,
    }