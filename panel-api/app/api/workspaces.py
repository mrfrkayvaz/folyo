import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from ..core.database import get_factory
from ..core.tables import t

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("")
async def list_workspaces():
    ws = await t("workspaces")
    doc = await t("documents")
    cm = await t("chat_messages")
    async with get_factory()() as s:
        rows = (
            await s.execute(
                select(ws.c.id, ws.c.name, ws.c.summary, ws.c.created_at)
                .order_by(ws.c.created_at.desc())
            )
        ).mappings().all()
        wids = [r["id"] for r in rows]
        doc_counts: dict = {}
        msg_counts: dict = {}
        if wids:
            doc_counts = {
                r["workspace_id"]: r["n"]
                for r in (
                    await s.execute(
                        select(doc.c.workspace_id, func.count().label("n"))
                        .where(doc.c.workspace_id.in_(wids))
                        .group_by(doc.c.workspace_id)
                    )
                ).mappings().all()
            }
            msg_counts = {
                r["workspace_id"]: r["n"]
                for r in (
                    await s.execute(
                        select(cm.c.workspace_id, func.count().label("n"))
                        .where(cm.c.workspace_id.in_(wids))
                        .group_by(cm.c.workspace_id)
                    )
                ).mappings().all()
            }
    return {
        "workspaces": [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "summary": r["summary"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "doc_count": doc_counts.get(r["id"]) or 0,
                "message_count": msg_counts.get(r["id"]) or 0,
            }
            for r in rows
        ]
    }


@router.get("/{wid}")
async def get_workspace(wid: uuid.UUID):
    ws = await t("workspaces")
    doc = await t("documents")
    async with get_factory()() as s:
        wrow = (
            await s.execute(
                select(ws.c.id, ws.c.name, ws.c.summary, ws.c.created_at).where(ws.c.id == wid)
            )
        ).mappings().one_or_none()
        if not wrow:
            raise HTTPException(404, "Workspace bulunamadı.")
        docs = (
            await s.execute(
                select(
                    doc.c.id, doc.c.filename, doc.c.file_type, doc.c.size, doc.c.status,
                    doc.c.chunk_count, doc.c.error, doc.c.summary, doc.c.summary_status,
                    doc.c.summary_error, doc.c.stats, doc.c.created_at, doc.c.updated_at,
                )
                .where(doc.c.workspace_id == wid)
                .order_by(doc.c.created_at.desc())
            )
        ).mappings().all()
    return {
        "workspace": {
            "id": str(wrow["id"]),
            "name": wrow["name"],
            "summary": wrow["summary"],
            "created_at": wrow["created_at"].isoformat() if wrow["created_at"] else None,
        },
        "documents": [
            {
                "id": str(r["id"]),
                "filename": r["filename"],
                "file_type": r["file_type"],
                "size": r["size"],
                "status": r["status"],
                "chunk_count": r["chunk_count"],
                "error": r["error"],
                "summary": r["summary"],
                "summary_status": r["summary_status"],
                "summary_error": r["summary_error"],
                "stats": r["stats"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in docs
        ],
    }