"""Belge embed hattı: extract → chunk → embed → Chroma → durum güncellemeleri.

Bu görev ARQ worker'ında (ayrı süreç) çalışır; web-api yalnızca kuyruğa atar.
"""

import uuid

from ...core import fs as core_fs
from ...core.config import get_settings
from ...core.database import get_factory
from ...core.enums import DocumentStatus, EmbeddingStatus
from ...core.logging import get_logger
from ...core.taskq import enqueue as taskq_enqueue
from ...models import Document, EmbeddingJob
from .. import bm25_index, chroma_codec, chroma_store, embeddings, ingest
from .cancel import EmbeddingCancelled, clear as clear_cancel, is_cancelled
from .paths import storage_dir
from .stats import compute_stats

LOG = get_logger("jobs.embed")


async def run_embed_job(workspace_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> None:
    settings = get_settings()
    sf = get_factory()
    file_path = storage_dir(document_id) / filename

    async def load_doc():
        async with sf() as s:
            return await s.get(Document, document_id)

    try:
        if await is_cancelled(str(document_id)):
            raise EmbeddingCancelled()

        doc = await load_doc()
        if doc is None or doc.status != DocumentStatus.pending:
            return

        async with sf() as s:
            job = await s.get(EmbeddingJob, document_id) or EmbeddingJob(id=document_id, document_id=document_id)
            job.status = EmbeddingStatus.running
            job.updated_at = job.updated_at.__class__.now()
            s.add(job)
            await s.commit()

        segments = await ingest.extract_segments_for(doc.filename, file_path, storage_dir(document_id) / "crops")
        chunks = ingest.chunk_segments(
            segments,
            settings.chunk_chars,
            settings.chunk_overlap,
            table_max_chars=settings.table_max_chars,
        )
        if not chunks:
            raise ValueError("Belgeden parçalanabilir metin çıkarılamadı.")

        async with sf() as s:
            doc = await s.get(Document, document_id)
            if doc:
                doc.status = DocumentStatus.embedding
                doc.updated_at = doc.updated_at.__class__.now()
                s.add(doc)
                await s.commit()

        async def on_progress(done: int) -> None:
            if await is_cancelled(str(document_id)):
                raise EmbeddingCancelled()
            async with sf() as s:
                job = await s.get(EmbeddingJob, document_id)
                if job:
                    job.progress = done
                    job.updated_at = job.updated_at.__class__.now()
                    s.add(job)
                    await s.commit()

        if len(chunks) > settings.embed_memory_warning_chunks:
            LOG.warning(
                "[embed] belge %s çok parçalı (%d chunk) — vektörler akışla yazılıyor",
                document_id,
                len(chunks),
            )

        dim_value: int | None = None

        async def write_batch(offset: int, vecs) -> None:
            """Tamamlanan her embedding batch'ini idempotent Chroma `upsert` ile yazar."""
            nonlocal dim_value
            batch = chunks[offset : offset + len(vecs)]
            if not batch:
                return
            if dim_value is None:
                dim_value = len(vecs[0])
            ids = [f"{document_id}:{c.chunk_index}" for c in batch]
            documents = [c.text for c in batch]
            metas = [
                chroma_codec.chunk_metadata(str(workspace_id), str(document_id), doc.filename, c)
                for c in batch
            ]
            await chroma_store.upsert_chunks(
                str(workspace_id), str(document_id), doc.filename, ids, documents, metas, vecs
            )

        # Akışlı embed: vektörler RAM'de toplanmaz, her batch bitince Chroma'ya yazılır.
        await embeddings.embed_batches([c.text for c in chunks], on_batch=write_batch, progress=on_progress)
        bm25_index.invalidate(workspace_id)

        dim = dim_value
        async with sf() as s:
            doc = await s.get(Document, document_id)
            if doc:
                doc.status = DocumentStatus.embedded
                doc.chunk_count = len(chunks)
                doc.error = None
                doc.stats = compute_stats(chunks)
                doc.updated_at = doc.updated_at.__class__.now()
                s.add(doc)
            job = await s.get(EmbeddingJob, document_id)
            if job:
                job.status = EmbeddingStatus.completed
                job.chunks = len(chunks)
                job.dim = dim
                job.progress = len(chunks)
                job.error = None
                job.updated_at = job.updated_at.__class__.now()
                s.add(job)
            await s.commit()

        try:
            await taskq_enqueue("enrich_document", str(workspace_id), str(document_id))
        except Exception as exc:
            LOG.warning("[embed] %s zenginleştirme kuyruğa atılamadı: %s", document_id, exc)

    except EmbeddingCancelled:
        await chroma_store.delete_document(document_id)
        await core_fs.rmtree_ignore(storage_dir(document_id))
        async with sf() as s:
            doc = await s.get(Document, document_id)
            if doc:
                doc.status = DocumentStatus.cancelled
                doc.updated_at = doc.updated_at.__class__.now()
                s.add(doc)
            job = await s.get(EmbeddingJob, document_id)
            if job:
                job.status = EmbeddingStatus.cancelled
                job.updated_at = job.updated_at.__class__.now()
                s.add(job)
            await s.commit()

    except Exception as exc:
        err_msg = str(exc)
        async with sf() as s:
            doc = await s.get(Document, document_id)
            if doc:
                doc.status = DocumentStatus.failed
                doc.error = err_msg
                doc.updated_at = doc.updated_at.__class__.now()
                s.add(doc)
            job = await s.get(EmbeddingJob, document_id)
            if job:
                job.status = EmbeddingStatus.failed
                job.error = err_msg
                job.updated_at = job.updated_at.__class__.now()
                s.add(job)
            await s.commit()
    finally:
        clear_cancel(str(document_id))