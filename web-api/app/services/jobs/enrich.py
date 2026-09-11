"""Belge özeti + workspace özeti işlemleri (embed sonrası asenkron zenginleştirme)."""

import asyncio
import uuid

from sqlmodel import select

from ...core.database import get_factory
from ...core.enums import SummaryStatus
from ...models import Document, DocumentQuestion, Workspace

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


async def enrich_summary(workspace_id: uuid.UUID, document_id: uuid.UUID, chunks) -> None:
    """Belge özetini + başlangıç sorularını üretir, tamamlanınca workspace özetini planlar."""
    from .. import summary as summary_svc

    try:
        await save_summary_status(document_id, SummaryStatus.pending)
        result = await summary_svc.generate_summary(chunks)
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
    except Exception as exc:
        await save_summary_status(document_id, SummaryStatus.failed, str(exc)[:800])
    finally:
        schedule_workspace_summary(workspace_id)


def schedule_workspace_summary(workspace_id) -> None:
    asyncio.create_task(delayed_workspace_summary(workspace_id))


async def delayed_workspace_summary(workspace_id) -> None:
    await asyncio.sleep(2)
    lock = _ws_guard.setdefault(str(workspace_id), asyncio.Lock())
    async with lock:
        await run_workspace_summary(workspace_id)


async def run_workspace_summary(workspace_id) -> None:
    """Yeni/kotarlanmış belge özetleri varsa workspace özetini yeniden üretir."""
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