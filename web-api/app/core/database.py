from pathlib import Path

import anyio
from sqlalchemy import inspect as _inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .config import get_settings
from .logging import get_logger

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


def _alembic(mode: str) -> None:
    """Alembic'i çalıştırır (upgrade head / stamp head). Şema kaynağı bu servisin
    modelleridir; CLI/calibration için `DATABASE_URL` env'i ile ezilebilir."""
    from alembic import command
    from alembic.config import Config

    base = Path(__file__).resolve().parents[1]  # web-api/app (alembic.ini + alembic/)
    cfg = Config(str(base / "alembic.ini"))
    cfg.set_main_option("script_location", str(base / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    if mode == "stamp":
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")


async def init_db() -> None:
    """Şema senkronu: alembic migration'larını uygular.

    - Yeni kurulum (tablolar yok) → `upgrade head` (schema'yı kurar).
    - Mevcut kurulum (eski `create_all` + ALTER'lar) → `stamp head` (veri kaldığı yerinde).
    - Alembic paketi yoksa (eski imaj) uyarı verip devam eder; tablolar zaten mevcuttur.
    """
    try:
        engine = create_async_engine(get_settings().database_url)
        async with engine.connect() as conn:
            has_documents = await conn.run_sync(lambda sc: _inspect(sc).has_table("documents"))
            has_version = await conn.run_sync(lambda sc: _inspect(sc).has_table("alembic_version"))
        await engine.dispose()
    except Exception as exc:
        LOG.warning("[init_db] şema denetimi yapılamadı: %s", exc)
        return

    mode = "stamp" if (has_documents and not has_version) else "upgrade"
    try:
        await anyio.to_thread.run_sync(_alembic, mode)
    except ImportError:
        LOG.warning(
            "[init_db] alembic paketi yüklü değil — migrasyon atlandı "
            "('docker compose build web-api' gerekli)."
        )
        return
    except Exception as exc:
        LOG.error("[init_db] migrasyon hatası: %s", exc, exc_info=True)
        raise

    # Eski etkin işleri başarısız say (restart/kesinti kalıntısı; recover yeniden zamanlar).
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
