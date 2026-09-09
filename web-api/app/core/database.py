from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from .config import get_settings

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


async def init_db() -> None:
    from ..models import Workspace  # noqa: F401 (ensure models are imported for metadata)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
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


async def get_session():
    async with get_factory()() as session:
        yield session
