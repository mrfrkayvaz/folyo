"""QA akışı — retrieval + LLM stream'ini SSE olaylarına dönüştürür (I/O katmanı)."""

import asyncio

from ...core.config import get_settings
from ...core.database import get_factory
from shared.core.constants import ERROR_NO_EMBEDDED_DOCS, ERROR_NO_SIMILAR_CONTEXT
from shared.services import bm25_index, chroma_store, embeddings, llm
from shared.services.qalogs import add_log as qa_log
from .retrieval import (
    _fusion,
    confidence_score,
    qualifying_intersections,
    sources,
)


async def qa_events(workspace_id, question: str, message_id=None):
    settings = get_settings()
    sf = get_factory()

    async def log(stage: str, level: str, msg: str) -> None:
        await qa_log(get_factory, workspace_id=workspace_id, message_id=message_id, level=level, stage=stage, message=msg)

    await log("başlangıç", "info", "QA isteği başladı")

    try:
        qvec = (await embeddings.embed_texts([question]))[0]
    except Exception as exc:
        await log("embedding", "error", f"Soru embedding'i başarısız: {exc}")
        yield {"type": "error", "message": f"Embedding hatası: {exc}"}
        return

    index, ws_chunks = await bm25_index.get_index(workspace_id)
    if not ws_chunks:
        await log("retrieval", "warning", "Embedlenmiş belge yok")
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
    await log(
        "retrieval", "info",
        f"Retrieval: dense={len(dense_hits)} bm25={len(bm25_hits)} "
        f"(en iyi dense={round(top_dense, 3)}, bm25={round(top_bm25, 3)})",
    )

    if not (top_dense >= settings.guard_dense_min or top_bm25 >= settings.guard_bm25_min):
        await log(
            "guard", "warning",
            f"Guard: yetersiz benzerlik (dense={round(top_dense, 3)} < {settings.guard_dense_min} "
            f"ve bm25={round(top_bm25, 3)} < {settings.guard_bm25_min}) — yanıt reddedildi",
        )
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
        await log("bağlam", "warning", "Füzyon sonrası bağlam boş")
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
    await log(
        "bağlam", "info",
        f"Bağlam: {len(ids)} chunk seçildi, belge={len({h['doc_id'] for h in hits})}, "
        f"güven={conf} ({level})",
    )

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

    await log("llm_başlangıç", "info", "LLM akışı başladı")
    task = asyncio.create_task(runner())
    delta_count = 0
    while True:
        kind, val = await queue.get()
        if kind == "delta":
            delta_count += 1
            yield {"type": "delta", "text": val}
        elif kind == "error":
            await log("llm_hata", "error", f"LLM hatası: {val}")
            yield {"type": "error", "message": f"LLM hatası: {val}"}
            break
        else:
            if delta_count == 0:
                await log(
                    "llm_sonuç", "error",
                    "LLM akışı hiç delta üretmeden tamamlandı (hata event'i de yok) — boş cevap",
                )
            else:
                await log("llm_sonuç", "info", f"LLM akışı tamam: {delta_count} delta")
            break
    await task
    yield {"type": "done", "sources": srcs, "chunk_ids": ids, "confidence": conf, "confidence_level": level}