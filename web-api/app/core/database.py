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
        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary_status TEXT"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS stats JSONB"))
        await conn.execute(text("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS summary TEXT"))
        await conn.execute(text("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS summary_docs JSONB"))
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS document_questions ("
                " id UUID PRIMARY KEY,"
                " document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,"
                " question TEXT NOT NULL,"
                " position INT NOT NULL,"
                " created_at TIMESTAMPTZ NOT NULL)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_document_questions_document_id "
                "ON document_questions(document_id)"
            )
        )
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
