import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..core.database import get_factory
from ..core.tables import t
from ..services.chunks import chunks_for

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/{did}")
async def get_document(did: uuid.UUID):
    doc = await t("documents")
    job_t = await t("embeddings")
    q_t = await t("document_questions")
    async with get_factory()() as s:
        d = (
            await s.execute(
                select(
                    doc.c.id, doc.c.workspace_id, doc.c.filename, doc.c.file_type, doc.c.size,
                    doc.c.status, doc.c.chunk_count, doc.c.error, doc.c.summary,
                    doc.c.summary_status, doc.c.summary_error, doc.c.stats,
                    doc.c.created_at, doc.c.updated_at,
                ).where(doc.c.id == did)
            )
        ).mappings().one_or_none()
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
        job = (
            await s.execute(
                select(
                    job_t.c.status, job_t.c.chunks, job_t.c.dim, job_t.c.progress,
                    job_t.c.error, job_t.c.created_at, job_t.c.updated_at,
                ).where(job_t.c.document_id == did)
            )
        ).mappings().one_or_none()
        qs = (
            await s.execute(
                select(q_t.c.question)
                .where(q_t.c.document_id == did)
                .order_by(q_t.c.position)
            )
        ).mappings().all()

    chunks = chunks_for(str(did))
    return {
        "document": {
            "id": str(d["id"]),
            "workspace_id": str(d["workspace_id"]),
            "filename": d["filename"],
            "file_type": d["file_type"],
            "size": d["size"],
            "status": d["status"],
            "chunk_count": d["chunk_count"],
            "error": d["error"],
            "summary": d["summary"],
            "summary_status": d["summary_status"],
            "summary_error": d["summary_error"],
            "questions": [q["question"] for q in qs],
            "stats": d["stats"],
            "created_at": d["created_at"].isoformat() if d["created_at"] else None,
            "updated_at": d["updated_at"].isoformat() if d["updated_at"] else None,
            "process": {
                "status": d["status"],
                "error": d["error"],
                "summary_status": d["summary_status"],
                "summary_error": d["summary_error"],
                "job": {
                    "status": job["status"] if job else None,
                    "chunks": job["chunks"] if job else None,
                    "dim": job["dim"] if job else None,
                    "progress": job["progress"] if job else 0,
                    "error": job["error"] if job else None,
                    "created_at": job["created_at"].isoformat() if job and job["created_at"] else None,
                    "updated_at": job["updated_at"].isoformat() if job and job["updated_at"] else None,
                },
            },
        },
        "chunks": chunks,
    }