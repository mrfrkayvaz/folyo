from fastapi import APIRouter
from sqlalchemy import select

from ..core.database import get_factory
from shared.models import ChatMessage, Document, Workspace

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    try:
        async with get_factory()() as s:
            ws = (await s.execute(select(Workspace))).scalars().all()
            docs = (await s.execute(select(Document))).scalars().all()
            msgs = (await s.execute(select(ChatMessage))).scalars().all()
        return {"status": "ok", "workspaces": len(ws), "documents": len(docs), "messages": len(msgs)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
