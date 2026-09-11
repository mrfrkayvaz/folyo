import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from ..core.database import get_factory
from ..models import ChatMessage, Document, Workspace

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("")
async def list_workspaces():
    async with get_factory()() as s:
        rows = (
            await s.execute(select(Workspace).order_by(Workspace.created_at.desc()))
        ).scalars().all()
        out = []
        for ws in rows:
            doc_count = (
                await s.execute(select(func.count()).select_from(Document).where(Document.workspace_id == ws.id))
            ).scalar()
            msg_count = (
                await s.execute(select(func.count()).select_from(ChatMessage).where(ChatMessage.workspace_id == ws.id))
            ).scalar()
            out.append(
                {
                    "id": str(ws.id),
                    "name": ws.name,
                    "summary": ws.summary,
                    "created_at": ws.created_at.isoformat() if ws.created_at else None,
                    "doc_count": doc_count or 0,
                    "message_count": msg_count or 0,
                }
            )
    return {"workspaces": out}


@router.get("/{wid}")
async def get_workspace(wid: uuid.UUID):
    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        docs = (
            await s.execute(select(Document).where(Document.workspace_id == wid).order_by(Document.created_at.desc()))
        ).scalars().all()
    return {
        "workspace": {
            "id": str(ws.id),
            "name": ws.name,
            "summary": ws.summary,
            "created_at": ws.created_at.isoformat() if ws.created_at else None,
        },
        "documents": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "size": d.size,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "error": d.error,
                "summary": d.summary,
                "summary_status": d.summary_status,
                "summary_error": d.summary_error,
                "stats": d.stats,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in docs
        ],
    }