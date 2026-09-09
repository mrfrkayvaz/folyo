import asyncio
import uuid

from ..core.config import get_settings
from ..core.constants import ERROR_NO_EMBEDDED_DOCS, ERROR_NO_SIMILAR_CONTEXT
from . import chroma_store, embeddings, llm


async def qa_events(workspace_id: uuid.UUID, question: str):
    settings = get_settings()

    try:
        qvec = (await embeddings.embed_texts([question]))[0]
    except Exception as exc:
        yield {"type": "error", "message": f"Embedding hatası: {exc}"}
        return

    raw_hits = await chroma_store.query(workspace_id, qvec, settings.top_k)
    if not raw_hits:
        yield {"type": "error", "message": ERROR_NO_EMBEDDED_DOCS}
        return

    threshold = settings.similarity_threshold
    hits = [h for h in raw_hits if h.get("score", 0.0) >= threshold]
    if not hits:
        yield {"type": "error", "message": ERROR_NO_SIMILAR_CONTEXT}
        return

    seen: dict[str, int] = {}
    order: list[str] = []
    for h in hits:
        if h["doc_id"] not in seen:
            seen[h["doc_id"]] = 0
            order.append(h["doc_id"])
        seen[h["doc_id"]] += 1

    sources = [
        {"label": next(h["name"] for h in hits if h["doc_id"] == d), "meta": f"{seen[d]} parça"}
        for d in order
    ]
    yield {"type": "meta", "sources": sources}

    q: asyncio.Queue = asyncio.Queue()

    async def runner() -> None:
        try:
            await llm.stream_deltas(hits, question, lambda d: q.put_nowait(("delta", d)))
            await q.put(("done", None))
        except Exception as exc:
            await q.put(("error", str(exc)))

    task = asyncio.create_task(runner())
    while True:
        kind, val = await q.get()
        if kind == "delta":
            yield {"type": "delta", "text": val}
        elif kind == "done":
            break
        elif kind == "error":
            yield {"type": "error", "message": f"LLM hatası: {val}"}
            break
    await task
    yield {"type": "done", "sources": sources}