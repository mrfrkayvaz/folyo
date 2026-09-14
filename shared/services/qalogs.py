"""Cevap (QA) üretim günlüğü (qa_logs tablosu).

web-api'nin QA pipeline'ı sahne sahne kaydeder: istek → embedding → retrieval →
guard → bağlam → LLM akışı → tamam/hata. Tam yanıt metni ASLA saklanmaz —
yalnızca olaylar (stage/level/message). Panel "Loglar" görünümü pagination'la okur.

Kullanım (web-api içinde):
    await add_log(get_factory, workspace_id=wid, message_id=msg_id,
                  stage="retrieval", message="dense=8 bm25=6")

`add_log` best-effort'tur: kayıt başarısız olursa yalnızca uyarı loglanır,
QA akışı asla bozulmaz.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from shared.core.logging import get_logger
from shared.models import QaLog

LOG = get_logger("services.qalogs")

# async_sessionmaker: `factory()()` → async session
Factory = Callable[[], Awaitable[Any]]


async def add_log(
    factory: Factory,
    *,
    workspace_id: uuid.UUID | str,
    message_id: uuid.UUID | str | None = None,
    level: str = "info",
    stage: str = "",
    message: str = "",
) -> None:
    """QA pipeline sahnesini tek satır olarak ekler (kendi session'ıyla)."""
    try:
        async with factory()() as s:
            s.add(
                QaLog(
                    workspace_id=workspace_id,
                    message_id=message_id,
                    level=level,
                    stage=stage,
                    message=message,
                    created_at=datetime.now(timezone.utc),
                )
            )
            await s.commit()
    except Exception as exc:  # noqa: BLE001 — best-effort kayıt
        LOG.warning("[qalogs] günlük yazılamadı (ws=%s): %s", workspace_id, exc)