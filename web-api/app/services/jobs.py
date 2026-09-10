import asyncio
import shutil
import uuid
from pathlib import Path

from ..core.config import get_settings
from ..core.database import get_factory
from ..core.enums import DocumentStatus, EmbeddingStatus
from ..models import Document, DocumentQuestion, EmbeddingJob
from . import chroma_store, embeddings, ingest


class EmbeddingCancelled(Exception):
    pass


_cancel_events: dict[str, asyncio.Event] = {}


def request_cancel(document_id: str) -> None:
    _cancel_events.setdefault(document_id, asyncio.Event()).set()


async def _is_cancelled(document_id: str) -> bool:
    ev = _cancel_events.get(document_id)
    return bool(ev and ev.is_set())


def storage_dir(document_id: uuid.UUID) -> Path:
    return Path(get_settings().storage_dir) / str(document_id)


async def run_embed_job(workspace_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> None:
    settings = get_settings()
    sf = get_factory()
    file_path = storage_dir(document_id) / filename

    async def load_doc():
        async with sf() as s:
            return await s.get(Document, document_id)

    try:
        if await _is_cancelled(str(document_id)):
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

        segments = await ingest.extract_segments_for(doc.filename, file_path)
        chunks = ingest.chunk_segments(segments, settings.chunk_chars, settings.chunk_overlap)
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
            if await _is_cancelled(str(document_id)):
                raise EmbeddingCancelled()
            async with sf() as s:
                job = await s.get(EmbeddingJob, document_id)
                if job:
                    job.progress = done
                    job.updated_at = job.updated_at.__class__.now()
                    s.add(job)
                    await s.commit()

        vectors = await embeddings.embed_texts([c.text for c in chunks], progress=on_progress)

        await chroma_store.add(str(workspace_id), str(document_id), doc.filename, chunks, vectors)

        dim = len(vectors[0]) if len(vectors) > 0 else None
        async with sf() as s:
            doc = await s.get(Document, document_id)
            if doc:
                doc.status = DocumentStatus.embedded
                doc.chunk_count = len(chunks)
                doc.error = None
                doc.stats = _compute_stats(chunks)
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

        asyncio.create_task(_enrich_summary(document_id, chunks))

    except EmbeddingCancelled:
        await chroma_store.delete_document(document_id)
        shutil.rmtree(storage_dir(document_id), ignore_errors=True)
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
        _cancel_events.pop(str(document_id), None)


async def _enrich_summary(document_id: uuid.UUID, chunks) -> None:
    """Embedding sonrası non-blocking özet + starter sorular (rag_arch §4).

    Hata veya model isteksizliği belgeyi asla `failed` yapmaz; özet boş kalır.
    """
    from . import summary as summary_svc

    try:
        result = await summary_svc.generate_summary(chunks)
        if not result:
            return
        async with get_factory()() as s:
            doc = await s.get(Document, document_id)
            if not doc:
                return
            doc.summary = result["summary"]
            doc.updated_at = doc.updated_at.__class__.now()
            s.add(doc)
            for i, q in enumerate(result["questions"]):
                s.add(DocumentQuestion(document_id=document_id, question=q, position=i))
            await s.commit()
    except Exception:
        pass


def _compute_stats(chunks) -> dict:
    """Kimlik kartı verisi: sayfa adedi, chunk adedi, tür dağılımı."""
    types: dict[str, int] = {}
    pages: set[int] = set()
    for c in chunks:
        types[c.content_type] = types.get(c.content_type, 0) + 1
        pages.add(c.page_number)
    return {"pages": len(pages), "chunks": len(chunks), "types": types}