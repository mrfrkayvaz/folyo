"""Belge özeti + workspace özeti işlemleri (embed sonrası zenginleştirme — ARQ kuyruğu).

Bu modüldeki görevler ayrı `web-worker` sürecinde (arq) yürütülür:
- `enrich_document` — belge özeti + starter sorular; chunk'ları Chroma'dan yeniden okur
  (kuyruk dayanıklılığı: argüman olarak chunk taşınmaz).
- `do_workspace_summary` — belge özetlerinin sentezi (workspace başına lock).
- `schedule_workspace_summary` — workspace özetini 2 sn ertelenmiş kuyruğa bırakır.
"""

import asyncio
import uuid

from sqlmodel import select

from ...core.database import get_factory
from shared.core.enums import SummaryStatus
from shared.core.logging import get_logger
from shared.services.jobs.schedule import schedule_workspace_summary
from shared.services.doclogs import add_log as add_doc_log
from shared.models import Document, DocumentQuestion, Workspace
from shared.services import chroma_store
from shared.services.types import Chunk

LOG = get_logger("jobs.enrich")

_ws_guard: dict[str, asyncio.Lock] = {}


async def save_summary_status(document_id: uuid.UUID, status: SummaryStatus, error: str | None = None) -> None:
    try:
        async with get_factory()() as s:
            doc = await s.get(Document, document_id)
            if doc:
                doc.summary_status = status.value
                doc.summary_error = error
                doc.updated_at = doc.updated_at.__class__.now()
                s.add(doc)
                await s.commit()
    except Exception:
        pass


def _chunks_from_rows(rows: list[dict]) -> list[Chunk]:
    """Chroma satırlarını özet üretiminin beklediği `Chunk` nesnelerine çevirir."""
    return [
        Chunk(
            text=c["text"],
            content_type=c.get("content_type", "text"),
            page_number=c.get("page_number", 1),
            page_context=c.get("page_context", ""),
            chunk_index=c.get("chunk_index", 0),
        )
        for c in rows
    ]


async def enrich_document(workspace_id: uuid.UUID, document_id: uuid.UUID) -> None:
    """Belge özetini + başlangıç sorularını üretir; sonunda workspace özetini planlar."""
    from .. import summary as summary_svc

    try:
        # Kuyruk dayanıklılığı: chunk'ları Chroma'dan tekrar oku (görev argümanı taşımaz).
        rows = await chroma_store.get_chunks_by_document(str(document_id))
        if not rows:
            return
        chunks = _chunks_from_rows(rows)
        await save_summary_status(document_id, SummaryStatus.pending)
        await add_doc_log(
            get_factory, workspace_id=workspace_id, document_id=document_id,
            scope="özet", message=f"Özet + önerilen sorular üretiliyor ({len(chunks)} chunk)",
        )
        result = await summary_svc.generate_summary(chunks)
        if not result:
            return
        async with get_factory()() as s:
            doc = await s.get(Document, document_id)
            if not doc:
                return
            old = (
                await s.execute(
                    select(DocumentQuestion).where(DocumentQuestion.document_id == document_id)
                )
            ).scalars().all()
            for q in old:
                s.delete(q)
            doc.summary = result["summary"]
            doc.summary_status = SummaryStatus.done.value
            doc.summary_error = None
            doc.updated_at = doc.updated_at.__class__.now()
            s.add(doc)
            for i, q in enumerate(result["questions"]):
                s.add(DocumentQuestion(document_id=document_id, question=q, position=i))
            await s.commit()
        await add_doc_log(
            get_factory, workspace_id=workspace_id, document_id=document_id,
            scope="özet",
            message=f"Özet hazır ({len(result['questions'])} önerilen soru)",
        )
    except Exception as exc:
        await add_doc_log(
            get_factory, workspace_id=workspace_id, document_id=document_id,
            level="error", scope="özet", message=f"Özet hatası: {str(exc)[:800]}",
        )
        await save_summary_status(document_id, SummaryStatus.failed, str(exc)[:800])
    finally:
        await schedule_workspace_summary(workspace_id)


async def do_workspace_summary(workspace_id: uuid.UUID) -> None:
    """Yeni/kotarlanmış belge özetleri varsa workspace özetini yeniden üretir (ws başına lock)."""
    lock = _ws_guard.setdefault(str(workspace_id), asyncio.Lock())
    async with lock:
        await _run_workspace_summary(workspace_id)


async def _run_workspace_summary(workspace_id: uuid.UUID) -> None:
    from .. import summary as summary_svc

    try:
        async with get_factory()() as s:
            ws = await s.get(Workspace, workspace_id)
            if not ws:
                return
            docs = (
                await s.execute(select(Document).where(Document.workspace_id == workspace_id))
            ).scalars().all()
            if not docs:
                return
            if any(d.summary_status == SummaryStatus.pending.value for d in docs):
                return
            done = [d for d in docs if d.summary and d.summary_status in (SummaryStatus.done.value, None)]
            if not done:
                return
            signature = sorted(str(d.id) for d in docs)
            if ws.summary_docs == signature:
                return

        inputs = [{"name": d.filename, "summary": d.summary} for d in done]
        result = await summary_svc.generate_workspace(inputs)
        if not result:
            return

        async with get_factory()() as s:
            ws = await s.get(Workspace, workspace_id)
            if not ws:
                return
            ws.summary = result["summary"]
            ws.name = result["title"] or ws.name
            ws.summary_docs = signature
            s.add(ws)
            await s.commit()
    except Exception:
        pass