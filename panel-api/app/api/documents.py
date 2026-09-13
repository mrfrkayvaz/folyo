import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..core.database import get_factory
from ..core.security import require_auth
from shared.models import Document, DocumentLog, DocumentQuestion, EmbeddingJob
from ..services.chunks import chunks_for

router = APIRouter(prefix="/api/documents", tags=["documents"], dependencies=[Depends(require_auth)])


@router.get("/{did}")
async def get_document(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        job = (
            await s.execute(select(EmbeddingJob).where(EmbeddingJob.document_id == did))
        ).scalar_one_or_none()
        qs = (
            await s.execute(
                select(DocumentQuestion.question)
                .where(DocumentQuestion.document_id == did)
                .order_by(DocumentQuestion.position)
            )
        ).scalars().all()
        # Loglar: en yeni 200 kayıt, görüntüleme sırası eski→yeni (chronological)
        log_rows = (
            await s.execute(
                select(DocumentLog)
                .where(DocumentLog.document_id == did)
                .order_by(DocumentLog.created_at.desc())
                .limit(200)
            )
        ).scalars().all()

    chunks = chunks_for(str(did))
    logs = [
        {
            "id": str(l.id),
            "level": l.level,
            "scope": l.scope,
            "message": l.message,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in reversed(log_rows)
    ]
    return {
        "document": {
            "id": str(d.id),
            "workspace_id": str(d.workspace_id),
            "filename": d.filename,
            "file_type": d.file_type,
            "size": d.size,
            "status": d.status.value,
            "chunk_count": d.chunk_count,
            "error": d.error,
            "summary": d.summary,
            "summary_status": d.summary_status,
            "summary_error": d.summary_error,
            "questions": list(qs),
            "stats": d.stats,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "process": {
                "status": d.status.value,
                "error": d.error,
                "summary_status": d.summary_status,
                "summary_error": d.summary_error,
                "job": {
                    "status": job.status.value if job else None,
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
        "logs": logs,
    }