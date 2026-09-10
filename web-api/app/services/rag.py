import asyncio

from ..core.config import get_settings
from ..core.constants import ERROR_NO_EMBEDDED_DOCS, ERROR_NO_SIMILAR_CONTEXT
from . import bm25_index, chroma_store, embeddings, llm


def _fusion(dense_hits: list[dict], bm25_hits: list[dict], k: int) -> list[dict]:
    merged: dict[tuple, dict] = {}
    for i, h in enumerate(dense_hits):
        key = (h["doc_id"], h["chunk_index"])
        merged.setdefault(key, {"hit": h, "dense_rank": i, "bm25_rank": None})
    for i, h in enumerate(bm25_hits):
        key = (h["doc_id"], h["chunk_index"])
        entry = merged.setdefault(key, {"hit": h, "dense_rank": None, "bm25_rank": i})
        entry["bm25_rank"] = i

    for e in merged.values():
        rrf = 0.0
        if e["dense_rank"] is not None:
            rrf += 1.0 / (k + e["dense_rank"] + 1)
        if e["bm25_rank"] is not None:
            rrf += 1.0 / (k + e["bm25_rank"] + 1)
        e["rrf"] = rrf
    return sorted(merged.values(), key=lambda e: e["rrf"], reverse=True)


def confidence(fused: list[dict]) -> tuple[int, str]:
    both = sum(1 for e in fused if e["dense_rank"] is not None and e["bm25_rank"] is not None)
    if both >= 2:
        return 92, "yüksek"
    if both == 1:
        return 82, "orta"
    return 72, "dolaylı"


def sources(hits: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    order: list[str] = []
    for h in hits:
        if h["doc_id"] not in seen:
            seen[h["doc_id"]] = 0
            order.append(h["doc_id"])
        seen[h["doc_id"]] += 1
    return [
        {"label": next(h["name"] for h in hits if h["doc_id"] == d), "meta": f"{seen[d]} parça"}
        for d in order
    ]


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
    conf, level = confidence(fused[: settings.context_chunks])
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