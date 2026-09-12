"""ARQ (Redis) görev kuyruğu istemcisi.

Web-api bu modülle görev ÜRETİR (embed/enrich); görevleri ayrı `web-worker`
süreci (arq worker) TÜKETİR. Redis yoksa `enqueue` hata fırlatır — çağıran
loglayıp bırakır; belge `pending`'de kalır ve sonraki açılışta `recover` yeniden
kuyruğa atar (idempotent).
"""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from .config import get_settings

_pool: ArqRedis | None = None


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def enqueue(name: str, *args, **kwargs):
    """Görevi kuyruğa bırakır (`_defer_by` saniye ile ertelenebilir)."""
    pool = await get_pool()
    return await pool.enqueue_job(name, *args, **kwargs)