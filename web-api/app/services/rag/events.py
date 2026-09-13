"""QA akışı — retrieval + LLM stream'ini SSE olaylarına dönüştürür (I/O katmanı)."""

import asyncio

from ...core.config import get_settings
from shared.core.constants import ERROR_NO_EMBEDDED_DOCS, ERROR_NO_SIMILAR_CONTEXT
from shared.services import bm25_index, chroma_store, embeddings, llm
from .retrieval import (
    _fusion,
    confidence_score,
    qualifying_intersections,
    sources,
)


async def qa_events(workspace_id, question: str):
    settings = get_settings()

    try:
        qvec = (await embeddings.embed_texts([question]))[0]
    except Exception as exc:
        yield {"type": "error", "message": f"Embedding hatası: {exc}"}
        return

    index, ws_chunks = await bm25_index.get_index(workspace_id)
    if not ws_chunks:
        yield {"type": "error", "message": ERROR_NO_EMBEDDED_DOCS}
        return

    dense_hits = await chroma_store.query(workspace_id, qvec, settings.retrieve_dense_k)

    bm25_hits: list[dict] = []
    bm25_scores: list[float] = []
    if index is not None:
        scores = index.get_scores(question)
        ranked = sorted(zip(ws_chunks, scores), key=lambda p: p[1], reverse=True)
        bm25_scores = [s for _, s in ranked]
        bm25_hits = [h for h, _ in ranked[: settings.retrieve_bm25_k]]

    bm25_by_key = {
        (h["doc_id"], h["chunk_index"]): s for h, s in zip(bm25_hits, bm25_scores)
    }

    top_dense = max((h["score"] for h in dense_hits), default=0.0)
    top_bm25 = max(bm25_scores, default=0.0)
    if not (top_dense >= settings.guard_dense_min or top_bm25 >= settings.guard_bm25_min):
        yield {
            "type": "meta",
            "sources": [],
            "chunk_ids": [],
            "confidence": round(top_dense * 100, 1),
            "confidence_level": "yetersiz",
            "rejected": True,
            "signals": {
                "dense": round(top_dense, 3),
                "bm25": round(top_bm25, 3),
                "dense_min": settings.guard_dense_min,
                "bm25_min": settings.guard_bm25_min,
            },
        }
        yield {"type": "error", "message": ERROR_NO_SIMILAR_CONTEXT}
        return

    fused = _fusion(dense_hits, bm25_hits, settings.rrf_k)
    hits = [e["hit"] for e in fused[: settings.context_chunks]]
    if not hits:
        yield {"type": "error", "message": ERROR_NO_SIMILAR_CONTEXT}
        return
    conf, level = confidence_score(
        top_dense=top_dense,
        top_bm25=top_bm25,
        qualifying=qualifying_intersections(
            fused[: settings.context_chunks],
            bm25_by_key,
            settings.guard_dense_min,
            settings.guard_bm25_min,
        ),
        context_k=settings.context_chunks,
        settings=settings,
    )
    srcs = sources(hits)
    ids = [f"{h['doc_id']}:{h['chunk_index']}" for h in hits]

    yield {
        "type": "meta",
        "sources": srcs,
        "chunk_ids": ids,
        "confidence": conf,
        "confidence_level": level,
        "rejected": False,
        "signals": {
            "dense": round(top_dense, 3),
            "bm25": round(top_bm25, 3),
            "dense_min": settings.guard_dense_min,
            "bm25_min": settings.guard_bm25_min,
        },
    }

    queue: asyncio.Queue = asyncio.Queue()

    async def runner():
        try:
            await llm.stream_deltas(hits, question, lambda d: queue.put_nowait(("delta", d)))
            await queue.put(("done", None))
        except Exception as exc:
            await queue.put(("error", str(exc)))

    task = asyncio.create_task(runner())
    while True:
        kind, val = await queue.get()
        if kind == "delta":
            yield {"type": "delta", "text": val}
        elif kind == "error":
            yield {"type": "error", "message": f"LLM hatası: {val}"}
            break
        else:
            break
    await task
    yield {"type": "done", "sources": srcs, "chunk_ids": ids, "confidence": conf, "confidence_level": level}