"""Restart/kesinti sonrası yetim embed işlerini kurtarır (lifespan başlangıcında).

Konteyner restart'ı veya uvicorn `--reload` sırasında in-flight `run_embed_job`
görevleri öldürülür; belgeler `pending`/`embedding`'de, job'lar olduğu durumda kalır.
Bu süpürme başlangıçta yalnızca BU işlem ömründen ÖNCE oluşturulmuş belgeleri tarar,
durumları sıfırlayıp job'u yeniden zamanlar (yarım Chroma eklemeleri temizlenir).
"""

import asyncio
from datetime import datetime, timezone

from sqlmodel import and_, or_, select

from ...core.database import get_factory
from ...core.enums import DocumentStatus, EmbeddingStatus
from ...core.logging import get_logger
from ...models import Document, EmbeddingJob
from .. import chroma_store
from .embed import run_embed_job

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

    seen: set[asyncio.Task] = set()
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

        task = asyncio.create_task(run_embed_job(d.workspace_id, d.id, d.filename))

        def _log(t: asyncio.Task, _did=doc.id) -> None:
            try:
                exc = t.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                LOG.warning(
                    "[embed-recovery] belge %s yeniden deneme başarısız",
                    _did,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

        task.add_done_callback(_log)
        seen.add(task)

    LOG.info("[embed-recovery] %d yetim iş yeniden zamanlandı.", len(rows))
    return len(rows)