"""panel-api şema tanımlamaz — yalnızca okur.

Şema kaynağı yalnızca web-api'dir (SQLModel modelleri + alembic migration'ları;
`web-api/app/alembic`). Bu modül, sorgu anında tabloları veritabanından
`autoload` ederek sütun/ad bilgisini kodda ikinci kez tanımlamadan çalışır —
schema drift riski yoktur; DB şeması neyse okunan odur.
"""

import asyncio

from sqlalchemy import MetaData, Table, create_engine, make_url
from sqlalchemy.pool import NullPool

from .database import get_settings

_tables: dict[str, Table] = {}
_LOADED = False


def _sync_engine():
    """Şema autoload için yalnızca okuma amaçlı senkron engine (psycopg).
    Veri işlemleri dahil tüm yazma akışı web-api'dedir; panel asla yazmaz."""
    url = make_url(get_settings().database_url).set(drivername="postgresql+psycopg")
    return create_engine(url, poolclass=NullPool)


def _load_sync() -> None:
    global _LOADED
    meta = MetaData()
    engine = _sync_engine()
    try:
        for name in ("workspaces", "documents", "document_questions", "embeddings", "chat_messages"):
            _tables[name] = Table(name, meta, autoload_with=engine)
    finally:
        engine.dispose()
    _LOADED = True


async def t(name: str) -> Table:
    """İstenen tabloya erişim; ilk çağrıda şema DB'den çekilir (thread'de, tek kez)."""
    if not _LOADED:
        await asyncio.to_thread(_load_sync)
    return _tables[name]