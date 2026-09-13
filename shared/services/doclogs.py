"""Doküman bazlı günlük kaydı (document_logs tablosu).

web-api (yükleme/iptal/silme) ve worker (embed/özet) süreçlerinin kilit adımları
zaman sıralı kaydedilir; panel "Loglar" sekmesi panel-api üzerinden okur.

Kullanım: çağıran kendi session üretecini verir (servis bazlı `get_factory`):
    await add_log(get_factory, workspace_id=wid, document_id=did,
                  scope="yükleme", message="Yükleme başladı")

`add_log` best-effort'tur: kayıt yazılamazsa yalnızca uyarı loglanır — asıl iş
akışı (upload/embed/summary) asla bozulmaz.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from shared.core.logging import get_logger
from shared.models import DocumentLog

LOG = get_logger("services.doclogs")

# async_sessionmaker: `factory()()` → async session
Factory = Callable[[], Awaitable[Any]]


async def add_log(
    factory: Factory,
    *,
    workspace_id: uuid.UUID | str,
    document_id: uuid.UUID | str,
    level: str = "info",
    scope: str = "",
    message: str = "",
) -> None:
    """Dokümana tek günlük satırı ekler (kendi session'ıyla, öncekini bozmaz)."""
    try:
        async with factory()() as s:
            s.add(
                DocumentLog(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    level=level,
                    scope=scope,
                    message=message,
                    created_at=datetime.now(timezone.utc),
                )
            )
            await s.commit()
    except Exception as exc:  # noqa: BLE001 — best-effort kayıt
        LOG.warning("[doclogs] günlük yazılamadı (doc=%s): %s", document_id, exc)


async def log_cancel(factory: Factory, *, workspace_id: uuid.UUID | str, document_id: uuid.UUID | str, message: str) -> None:
    await add_log(factory, workspace_id=workspace_id, document_id=document_id, level="warning", scope="sistem", message=message)