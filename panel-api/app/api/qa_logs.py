"""Cevap (QA) günlükleri — pagination'lı okuma (panel 'Loglar' görünümü).

Öğeler en yeni en üstte; sayfa başına `limit`, toplam/pages ile istemci
pagination kontrolü yapar. `workspace_id` ve `level` ile filtrelenebilir.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from ..core.database import get_factory
from ..core.security import require_auth
from shared.models import QaLog, Workspace

router = APIRouter(prefix="/api/qa-logs", tags=["qa-logs"], dependencies=[Depends(require_auth)])


@router.get("")
async def list_qa_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    workspace_id: str | None = None,
    level: str | None = None,
):
    ws_alias = aliased(Workspace)
    base = select(QaLog).join(ws_alias, QaLog.workspace_id == ws_alias.id)
    if workspace_id:
        base = base.where(QaLog.workspace_id == workspace_id)
    if level:
        base = base.where(QaLog.level == level)

    stmt = base.order_by(QaLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    count_stmt = select(func.count()).select_from(
        QaLog.__table__.join(ws_alias.__table__, QaLog.workspace_id == ws_alias.__table__.c.id)
    )
    if workspace_id:
        count_stmt = count_stmt.where(QaLog.workspace_id == workspace_id)
    if level:
        count_stmt = count_stmt.where(QaLog.level == level)

    async with get_factory()() as s:
        rows = (await s.execute(stmt)).scalars().all()
        ws_names = {
            wid: name
            for wid, name in (
                await s.execute(select(ws_alias.id, ws_alias.name))
            ).all()
        }
        total = (await s.execute(count_stmt)).scalar_one()

    items = [
        {
            "id": str(l.id),
            "workspace_id": str(l.workspace_id),
            "workspace_name": ws_names.get(str(l.workspace_id), ""),
            "message_id": str(l.message_id) if l.message_id else None,
            "level": l.level,
            "stage": l.stage,
            "message": l.message,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in rows
    ]
    pages = max(1, -(-total // limit))
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": pages,
    }