from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .config import get_settings
from shared.core.logging import get_logger

LOG = get_logger("core.database")

_engine: AsyncEngine | None = None
_factory: async_sessionmaker | None = None


def get_engine() -> AsyncEngine:
    global _engine, _factory
    if _engine is None:
        url = get_settings().database_url
        if not url:
            raise RuntimeError(
                "DATABASE_URL tanımlı değil. web-api/.env dosyasına ekleyin, örnek:\n"
                "  DATABASE_URL=postgresql+asyncpg://folyo:folyo@localhost:5432/folyo\n"
                "DB'yi başlatmak için: docker compose up -d db"
            )
        _engine = create_async_engine(url, echo=False)
        _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_factory() -> async_sessionmaker:
    get_engine()
    assert _factory is not None
    return _factory


async def reset_interrupted_jobs() -> None:
    """Restart/kesintiyle orta durumda kalmış embed görevlerini başarısız sayar.

    Not: Şema migrasyonu panel-api'ye taşındı (init_db orada); bu fonksiyon yalnızca
    kuyruk durumlarını sıfırlar (recover_orphaned_jobs yeniden zamanlar).
    """
    try:
        async with get_factory()() as session:
            await session.execute(
                text("UPDATE documents SET status='failed', updated_at=now() "
                     "WHERE status IN ('uploading','pending','embedding')")
            )
            await session.execute(
                text("UPDATE embeddings SET status='failed', updated_at=now() "
                     "WHERE status IN ('pending','running')")
            )
            await session.commit()
    except Exception as exc:
        LOG.warning("[reset] kuyruk durumları sıfırlanamadı: %s", exc)


async def get_session():
    async with get_factory()() as session:
        yield session