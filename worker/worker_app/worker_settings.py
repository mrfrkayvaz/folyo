"""ARQ worker ayarları — `arq app.worker_settings.settings` ile başlar.

Fonksiyonlar `worker_runners`'daki sarmalayıcılardır; görev adları web-api'nin
`core/taskq.enqueue` çağrılarıyla eşleşir. Redis URL'si worker/.env'den gelir.
"""

from arq.connections import RedisSettings
from arq.worker import func

from .core.config import get_settings

# Ortak (shared) modüller bu worker'ın Settings nesnesini kullanır — shared importları
# bind'den SONRA gelmelidir (embeddings modül-importta get_settings() çağırır).
from shared.core import config as _shared_config

_shared_config.bind(get_settings())

from .worker_runners import embed_document, enrich_document, workspace_summary

settings = dict(
    functions=[
        func(embed_document, name="embed_document", timeout=1800, keep_result=0, max_tries=3),
        func(enrich_document, name="enrich_document", timeout=300, keep_result=0, max_tries=3),
        func(workspace_summary, name="workspace_summary", timeout=300, keep_result=0, max_tries=3),
    ],
    redis_settings=RedisSettings.from_dsn(get_settings().redis_url),
    max_jobs=4,
    job_timeout=1800,
    keep_result=0,
    max_tries=3,
    retry_jobs=True,
    health_check_interval=15,
)