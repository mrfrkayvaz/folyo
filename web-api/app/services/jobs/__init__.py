"""web-api'nin worker'a dokunduğu sınır: iptal isteği + özet planlama + depolama yolu.

Görev gövdeleri (embed/enrich) ayrı `worker_app` servisinde çalışır; bu paket
yalnızca web-api'nin ihtiyaç duyduğu kontrol yüzeyini taşır. Not: `recover_orphaned_jobs`
API başlangıcında yetim işleri düzeltmek için web-api'de kalır (lifespan).
"""

from shared.services.jobs.cancel import EmbeddingCancelled, request_cancel
from shared.services.jobs.schedule import schedule_workspace_summary
from shared.services.paths import storage_dir

__all__ = [
    "EmbeddingCancelled",
    "request_cancel",
    "schedule_workspace_summary",
    "storage_dir",
]