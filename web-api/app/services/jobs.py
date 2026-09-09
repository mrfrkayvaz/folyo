"""Arka plan embedding görevi + iptal bayrakları.

Dosya yüklendikten sonra `run_embed_job` asyncio görevi olarak başlatılır:
  embeddings(pending→running) → OpenRouter embed (batch'ler arası iptal kontrolü)
  → chroma'ya yaz → completed / embedded
İptal: `request_cancel(doc_id)` → görev bir sonraki batch'te durur,
kısmi chroma kaydı + dosya silinir, durumlar cancelled olur.
"""

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Callable

from ..config import get_settings
from ..db import get_factory
from ..models import Document, DocumentStatus, EmbeddingJob, EmbeddingStatus
from . import chroma_store, embeddings, ingest


class EmbeddingCancelled(Exception):
    """Kullanıcı iptal etti — kayıt temizlenir."""


_cancel_events: dict[str, asyncio.Event] = {}


def request_cancel(document_id: str) -> None:
    _cancel_events.setdefault(document_id, asyncio.Event()).set()


async def _is_cancelled(document_id: str) -> bool:
    ev = _cancel_events.get(document_id)
    return bool(ev and ev.is_set())


def _storage_path(document_id: uuid.UUID) -> Path:
    return Path(get_settings().storage_dir) / str(document_id)


async def run_embed_job(workspace_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> None:
    settings = get_settings()
    sf = get_factory()
    file_path = _storage_path(document_id) / filename

    async def load_doc():
        async with sf() as s:
            return await s.get(Document, document_id)

    try:
        # wikipedia gibi hızlı iptal kontrolü
        if await _is_cancelled(str(document_id)):
            raise EmbeddingCancelled()

        doc = await load_doc()
        if doc is None or doc.status != DocumentStatus.pending:
            return  # silinmiş/kullanıcı iptali zaten yapılmış

        job_id = None
        async with sf() as s:
            job = await s.get(EmbeddingJob, document_id) or EmbeddingJob(id=document_id, document_id=document_id)
            job.status = EmbeddingStatus.running
            job.updated_at = job.updated_at.__class__.now()
            s.add(job)
            await s.commit()
            job_id = job.id

        # 1) metin + parçalar
        text = ingest.extract_text_for(doc.filename, file_path)
        chunks = ingest.chunk_text(text, settings.chunk_chars, settings.chunk_overlap)
        if not chunks:
            raise ValueError("Belgeden parçalanabilir metin çıkarılamadı.")

        # 2) durum: embedding
        async with sf() as s:
            doc = await s.get(Document, document_id)
            doc.status = DocumentStatus.embedding
            doc.updated_at = doc.updated_at.__class__.now()
            s.add(doc)
            await s.commit()

        # 3) embed (batch'ler arası iptal kontrolü)
        async def on_progress(done: int) -> None:
            if await _is_cancelled(str(document_id)):
                raise EmbeddingCancelled()
            async with sf() as s:
                job = await s.get(EmbeddingJob, document_id)
                if job:
                    job.progress = done
                    job.updated_at = job.updated_at.__class__.now()
                    s.add(job)
                    await s.commit()

        vectors = await embeddings.embed_texts(chunks, progress=on_progress)

        # 4) chroma
        await chroma_store.add(str(workspace_id), str(document_id), doc.filename, chunks, vectors)

        # 5) tamamlandı
        async with sf() as s:
            job = await s.get(EmbeddingJob, document_id)
            job.status = EmbeddingStatus.completed
            job.chunks = len(chunks)
            job.dim = int(vectors.shape[1])
            job.progress = len(chunks)
            job.updated_at = job.updated_at.__class__.now()
            s.add(job)
            doc = await s.get(Document, document_id)
            doc.status = DocumentStatus.embedded
            doc.chunk_count = len(chunks)
            doc.updated_at = doc.updated_at.__class__.now()
            doc.error = None
            s.add(doc)
            await s.commit()

    except EmbeddingCancelled:
        await _cancel_cleanup(document_id, file_path)
    except Exception as exc:  # noqa: BLE001 — kullanıcıya net mesaj
        try:
            await chroma_store.delete_document(document_id)
        except Exception:
            pass
        async with sf() as s:
            job = await s.get(EmbeddingJob, document_id)
            if job:
                job.status = EmbeddingStatus.failed
                job.error = str(exc)
                job.updated_at = job.updated_at.__class__.now()
                s.add(job)
            doc = await s.get(Document, document_id)
            if doc and doc.status != DocumentStatus.cancelled:
                doc.status = DocumentStatus.failed
                doc.error = str(exc)
                doc.updated_at = doc.updated_at.__class__.now()
                s.add(doc)
            await s.commit()


async def _cancel_cleanup(document_id: uuid.UUID, file_path: Path) -> None:
    try:
        await chroma_store.delete_document(document_id)
    except Exception:
        pass
    shutil.rmtree(_storage_path(document_id), ignore_errors=True)
    sf = get_factory()
    async with sf() as s:
        job = await s.get(EmbeddingJob, document_id)
        if job:
            job.status = EmbeddingStatus.cancelled
            job.updated_at = job.updated_at.__class__.now()
            s.add(job)
        doc = await s.get(Document, document_id)
        if doc:
            doc.status = DocumentStatus.cancelled
            doc.updated_at = doc.updated_at.__class__.now()
            s.add(doc)
        await s.commit()