import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select as sa_select
from sqlmodel import select as sm_select

from shared.core import fs as core_fs
from shared.core.constants import DEFAULT_WORKSPACE_NAME
from ..core.database import get_factory
from ..core.security import require_auth
from shared.models import ChatMessage, Document, DocumentQuestion, Workspace
from ..schemas.workspace import WorkspaceCreate
from shared.services import chroma_store
from ..services.jobs import storage_dir

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"], dependencies=[Depends(require_auth)])

# Chat geçmişi sayfalama: ilk yüklemede son N mesaj; en üstte imleçli eski parti.
MESSAGE_PAGE_SIZE = 10
MAX_MESSAGE_LIMIT = 50


def _message_out(m: ChatMessage) -> dict:
    return {
        "id": str(m.id),
        "role": m.role.value,
        "content": m.content,
        "citations": m.citations,
        "created_at": m.created_at.isoformat(),
    }


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
    # Her workspace'in son mesaj zamanı, ana sorguya bağıntılı (correlated) alt sorgu olarak gelir:
    # tek SQL, döngü/ayrı sorgu yok. (N+1'in olmadığı şekil — GROUP BY'sız en dolaysız ifade.)
    last_at_subq = (
        sa_select(func.max(ChatMessage.created_at))
        .where(ChatMessage.workspace_id == Workspace.id)
        .correlate(Workspace)
    ).scalar_subquery()
    async with get_factory()() as s:
        rows = (
            await s.execute(
                sa_select(Workspace, last_at_subq.label("last_message_at"))
                .order_by(Workspace.created_at.desc())
            )
        ).all()
        out = [
            {
                "id": str(ws.id),
                "name": ws.name,
                "summary": ws.summary,
                "created_at": ws.created_at.isoformat(),
                "last_message_at": last.isoformat() if last else None,
            }
            for ws, last in rows
        ]
    return {"workspaces": out}


@router.get("/{wid}")
async def get_workspace(wid: uuid.UUID):
    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        # Son N mesaj (kronolojik sıra korunur) + daha eski var mı?
        msg_rows = (
            await s.execute(
                sm_select(ChatMessage)
                .where(ChatMessage.workspace_id == wid)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(MESSAGE_PAGE_SIZE + 1)
            )
        ).scalars().all()
        has_more = len(msg_rows) > MESSAGE_PAGE_SIZE
        msgs = list(reversed(msg_rows[:MESSAGE_PAGE_SIZE]))
        docs = (await s.execute(sm_select(Document).where(Document.workspace_id == wid))).scalars().all()
        q_questions = []
        if docs:
            q_questions = (
                await s.execute(
                    sm_select(DocumentQuestion)
                    .where(DocumentQuestion.document_id.in_([d.id for d in docs]))
                    .order_by(DocumentQuestion.position)
                )
            ).scalars().all()
        q_by_doc: dict[uuid.UUID, list[str]] = {}
        for q in q_questions:
            q_by_doc.setdefault(q.document_id, []).append(q.question)
    return {
        "workspace": {
            "id": str(ws.id),
            "name": ws.name,
            "summary": ws.summary,
            "created_at": ws.created_at.isoformat(),
        },
        "messages": [_message_out(m) for m in msgs],
        "has_more": has_more,
        "documents": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "size": d.size,
                "status": d.status.value,
                "chunk_count": d.chunk_count,
                "error": d.error,
                "summary": d.summary,
                "summary_status": d.summary_status,
                "summary_error": d.summary_error,
                "stats": d.stats,
                "starter_questions": q_by_doc.get(d.id, []),
            }
            for d in docs
        ],
    }


@router.get("/{wid}/messages")
async def get_older_messages(
    wid: uuid.UUID,
    before_at: str | None = None,
    before_id: str | None = None,
    limit: int = MESSAGE_PAGE_SIZE,
):
    """İmleç tabanlı eski mesaj getirme: `(created_at, id) < (before_at, before_id)`
    koşuluyla bir önceki sayfanın en eski mesajının öncesini döndürür (kronolojik)."""
    limit = max(1, min(limit, MAX_MESSAGE_LIMIT))
    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        stmt = sm_select(ChatMessage).where(ChatMessage.workspace_id == wid)
        before_ts = None
        if before_at:
            try:
                before_ts = datetime.fromisoformat(before_at.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(422, "before_at geçersiz (ISO tarih beklenir).")
        if before_ts is not None:
            if before_id:
                try:
                    before_uuid = uuid.UUID(before_id)
                except ValueError:
                    raise HTTPException(422, "before_id geçersiz.")
                # Eşzamanlı kayıtlarda kararlı kırpma: (tarih, id) demeti karşılaştırması.
                stmt = stmt.where(
                    or_(
                        ChatMessage.created_at < before_ts,
                        and_(ChatMessage.created_at == before_ts, ChatMessage.id < before_uuid),
                    )
                )
            else:
                stmt = stmt.where(ChatMessage.created_at < before_ts)
        rows = (
            await s.execute(
                stmt.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit + 1)
            )
        ).scalars().all()
    has_more = len(rows) > limit
    msgs = list(reversed(rows[:limit]))
    return {"messages": [_message_out(m) for m in msgs], "has_more": has_more}


@router.delete("/{wid}")
async def delete_workspace(wid: uuid.UUID):
    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        docs = (await s.execute(sa_select(Document).where(Document.workspace_id == wid))).scalars().all()
        # Belge dosyalarını (storage) temizle; FK'lar DB'de ondelete=CASCADE ile halledilir.
        for d in docs:
            await core_fs.rmtree_ignore(storage_dir(d.id))
        await s.delete(ws)
        await s.commit()
    await chroma_store.delete_workspace(wid)
    return {"deleted": True}
