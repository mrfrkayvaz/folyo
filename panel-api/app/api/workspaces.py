import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..core.database import get_factory
from ..core.security import require_auth
from shared.models import ChatMessage, Document, Workspace

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"], dependencies=[Depends(require_auth)])


@router.get("")
async def list_workspaces():
    async with get_factory()() as s:
        rows = (
            await s.execute(
                select(Workspace.id, Workspace.name, Workspace.summary, Workspace.created_at)
                .order_by(Workspace.created_at.desc())
            )
        ).all()
        wids = [r.id for r in rows]
        doc_counts: dict = {}
        msg_counts: dict = {}
        if wids:
            doc_counts = {
                r[0]: r[1]
                for r in (
                    await s.execute(
                        select(Document.workspace_id, func.count())
                        .where(Document.workspace_id.in_(wids))
                        .group_by(Document.workspace_id)
                    )
                ).all()
            }
            msg_counts = {
                r[0]: r[1]
                for r in (
                    await s.execute(
                        select(ChatMessage.workspace_id, func.count())
                        .where(ChatMessage.workspace_id.in_(wids))
                        .group_by(ChatMessage.workspace_id)
                    )
                ).all()
            }
    return {
        "workspaces": [
            {
                "id": str(r.id),
                "name": r.name,
                "summary": r.summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "doc_count": doc_counts.get(r.id) or 0,
                "message_count": msg_counts.get(r.id) or 0,
            }
            for r in rows
        ]
    }


@router.get("/{wid}")
async def get_workspace(wid: uuid.UUID):
    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        docs = (
            await s.execute(
                select(
                    Document.id, Document.filename, Document.file_type, Document.size,
                    Document.status, Document.chunk_count, Document.error, Document.summary,
                    Document.summary_status, Document.summary_error, Document.stats,
                    Document.created_at, Document.updated_at,
                )
                .where(Document.workspace_id == wid)
                .order_by(Document.created_at.desc())
            )
        ).all()
    return {
        "workspace": {
            "id": str(ws.id),
            "name": ws.name,
            "summary": ws.summary,
            "created_at": ws.created_at.isoformat() if ws.created_at else None,
        },
        "documents": [
            {
                "id": str(r.id),
                "filename": r.filename,
                "file_type": r.file_type,
                "size": r.size,
                "status": r.status.value,
                "chunk_count": r.chunk_count,
                "error": r.error,
                "summary": r.summary,
                "summary_status": r.summary_status,
                "summary_error": r.summary_error,
                "stats": r.stats,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in docs
        ],
    }