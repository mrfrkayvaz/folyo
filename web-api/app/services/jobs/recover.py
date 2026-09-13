"""Restart/kesinti sonrası yetim embed işlerini kurtarır (lifespan başlangıcında).

Konteyner restart'ı veya uvicorn `--reload` sırasında in-flight `run_embed_job`
görevleri öldürülür; belgeler `pending`/`embedding`'de, job'lar olduğu durumda kalır.
Bu süpürme başlangıçta yalnızca BU işlem ömründen ÖNCE oluşturulmuş belgeleri tarar,
durumları sıfırlayıp job'u yeniden zamanlar (yarım Chroma eklemeleri temizlenir).
"""

from datetime import datetime, timezone

from sqlmodel import and_, or_, select

from ...core.database import get_factory
from shared.core.enums import DocumentStatus, EmbeddingStatus
from shared.core.logging import get_logger
from shared.core.taskq import enqueue as taskq_enqueue
from shared.models import Document, EmbeddingJob
from shared.services import chroma_store

LOG = get_logger("jobs.recover")


async def recover_orphaned_jobs() -> int:
    """Yetim embed işlerini yeniden işleme koyar; yeniden zamanlanan sayıyı döndürür."""
    started_at = datetime.now(timezone.utc)
    async with get_factory()() as s:
        rows = (
            await s.execute(
                select(Document, EmbeddingJob)
                .join(EmbeddingJob, EmbeddingJob.document_id == Document.id)
                .where(
                    Document.created_at < started_at,
                    or_(
                        # (1) Görev öldürülmüş: doc/job orta durumda kalmış.
                        and_(
                            Document.status.in_(
                                [DocumentStatus.pending.value, DocumentStatus.embedding.value]
                            ),
                            EmbeddingJob.status.in_(
                                [EmbeddingStatus.pending.value, EmbeddingStatus.running.value]
                            ),
                        ),
                        # (2) Torn-write izi: failed ama hata mesajı yok ve hiç ilerleme yok —
                        #     gerçek bir başarısızlık değil, yazım sırasında kesilme.
                        and_(
                            Document.status == DocumentStatus.failed.value,
                            EmbeddingJob.status == EmbeddingStatus.failed.value,
                            EmbeddingJob.error.is_(None),
                            EmbeddingJob.progress == 0,
                        ),
                    ),
                )
            )
        ).all()

    if not rows:
        return 0

    queued = 0
    for doc, job in rows:
        # Yarım kalmış Chroma eklemesi olabilir — temizle (idempotent), sonra baştan.
        try:
            await chroma_store.delete_document(doc.id)
        except Exception:
            pass
        async with get_factory()() as s:
            d = await s.get(Document, doc.id)
            j = await s.get(EmbeddingJob, doc.id)
            if d is None or j is None:
                continue
            d.status = DocumentStatus.pending.value
            d.error = None
            j.status = EmbeddingStatus.pending.value
            j.error = None
            j.progress = 0
            s.add(d)
            s.add(j)
            await s.commit()

        # Embed görevini ARQ kuyruğuna bırak (worker süreci tüketir).
        try:
            await taskq_enqueue("embed_document", str(d.workspace_id), str(d.id), d.filename)
            queued += 1
        except Exception as exc:
            LOG.warning("[embed-recovery] belge %s kuyruğa atılamadı: %s", doc.id, exc)

    LOG.info("[embed-recovery] %d yetim iş kuyruğa yeniden atıldı.", queued)
    return queued