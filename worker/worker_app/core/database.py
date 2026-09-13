"""worker veritabanı erişimi — bağımsız (yalnızca asyncpg; şema/migrasyon panel-api'de)."""

import logging

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .config import get_settings

LOG = logging.getLogger("uvicorn.error.worker.database")

_engine: AsyncEngine | None = None
_factory: async_sessionmaker | None = None


def get_factory() -> async_sessionmaker:
    global _engine, _factory
    if _engine is None:
        url = get_settings().database_url
        if not url:
            raise RuntimeError("DATABASE_URL tanımlı değil (panel-api/.env → web-api/.env kaynak?).")
        _engine = create_async_engine(url, echo=False)
        _factory = async_sessionmaker(_engine, expire_on_commit=False)
    assert _factory is not None
    return _factory