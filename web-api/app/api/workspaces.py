import shutil
import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select as sm_select

from ..core.constants import DEFAULT_WORKSPACE_NAME
from ..core.database import get_factory
from ..models import ChatMessage, Document, Workspace
from ..schemas.workspace import WorkspaceCreate
from ..services import chroma_store
from ..services.jobs import storage_dir

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.post("")
async def create_workspace(body: WorkspaceCreate | None = None):
    name = (body.name if body else None) or DEFAULT_WORKSPACE_NAME
    ws = Workspace(name=name)
    async with get_factory()() as s:
        s.add(ws)
        await s.commit()
        await s.refresh(ws)
    return {"id": str(ws.id), "name": ws.name, "created_at": ws.created_at.isoformat()}


@router.get("")
async def list_workspaces():
    async with get_factory()() as s:
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


@router.get("/{wid}")
async def get_workspace(wid: uuid.UUID):
    async with get_factory()() as s:
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


@router.delete("/{wid}")
async def delete_workspace(wid: uuid.UUID):
    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        docs = list((await s.execute(sm_select(Document).where(Document.workspace_id == wid))).scalars())
        for d in docs:
            shutil.rmtree(storage_dir(d.id), ignore_errors=True)
        await s.delete(ws)
        await s.commit()
    await chroma_store.delete_workspace(wid)
    return {"deleted": True}
