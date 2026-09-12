import asyncio
import math

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


def _norm01(value: float, lo: float, hi: float) -> float:
    """Değeri 0-1 bandına lineer normalize eder (taşmalar kırpılır)."""
    if hi <= lo:
        return 1.0 if value >= hi else 0.0
    if value <= lo:
        return 0.0
    if value >= hi:
        return 1.0
    return (value - lo) / (hi - lo)


def level_for_score(score: float) -> str:
    """Sürekli güven skorundan (0-100) rozet seviyesi."""
    if score >= 85:
        return "yüksek"
    if score >= 65:
        return "orta"
    if score >= 45:
        return "dolaylı"
    return "yetersiz"


def qualifying_intersections(
    fused: list[dict],
    bm25_by_key: dict[tuple[str, int], float],
    dense_min: float,
    bm25_min: float,
) -> int:
    """Kesişen ve `dense ≥ dense_min` VEYA güçlü `BM25 ≥ bm25_min` şartını sağlayan parça sayısı.

    Dense skoru görmezden gelinemez: zayıf kesişimler sayılmaz.
    """
    n = 0
    for e in fused:
        if e["dense_rank"] is None or e["bm25_rank"] is None:
            continue
        hit = e["hit"]
        d = float(hit.get("score") or 0.0)
        b = float(bm25_by_key.get((hit["doc_id"], hit["chunk_index"]), 0.0))
        if d >= dense_min or b >= bm25_min:
            n += 1
    return n


def confidence_score(
    *,
    top_dense: float,
    top_bm25: float,
    qualifying: int,
    context_k: int,
    settings,
) -> tuple[float, str]:
    """Sürekli güven skoru (0-100) — taşıyıcı (carrier) modeli.

    Eski tek-formül (58·d + 24·b + 18·c) dense'u aşırı baskındı: BM25 nakavt etse
    (ör. kısa Türkçe sorgu + yapısal liste chunk'ı; dense ~0.2, BM25 6.8) skor 52'de
    kalıp tabel 55 tabanına çarpıyordu. İki bağımsız yol tanımlanır, her birinin
    ağırlıkları toplamı 100'dür ve kanıtı taşıyan yol skoru belirler:

    - **dense yolu** = `w_norm_d·d + (100 − w_norm_d)·c`  (semantik kanal baskın)
    - **bm25 yolu** = `w_norm_b·b + (100 − w_norm_b − bonus)·c + bonus·d` (sözlüksel kanal baskın)

    - `d = norm01(top_dense, 0.15, 0.70)` — BGE-M3 TR gerçekçi aralık.
    - `b = norm01(log1p(top_bm25), 0, log1p(5))` — BM25 log-ölçek.
    - `c = qualifying / context_k` — iki retrieverin birlikte geçtiği parça oranı.
    Kurallar: dense tamamen yokken güçlü BM25 (`b ≥ 0.5`) → taban 74 (eski
    "dense sıfırsa 75-80" kararı); kalkan geçmiş sorgu daima ≥ `confidence_min_answered`
    (yetersiz rozeti yalnız reddedilen sorgularda anlamlıdır).
    """
    d = _norm01(top_dense, settings.confidence_dense_min, settings.confidence_dense_max)
    b = _norm01(
        math.log1p(max(top_bm25, 0.0)),
        0.0,
        math.log1p(settings.confidence_bm25_sat),
    )
    c = min(qualifying / max(context_k, 1), 1.0)

    d_path = settings.confidence_path_dense_norm * d + (
        100.0 - settings.confidence_path_dense_norm
    ) * c
    b_path = (
        settings.confidence_path_bm25_norm * b
        + (100.0 - settings.confidence_path_bm25_norm - settings.confidence_path_kind_bonus) * c
        + settings.confidence_path_kind_bonus * d
    )
    score = max(d_path, b_path)
    if d <= 0.0 and b >= 0.5:
        score = max(score, settings.confidence_dense_blind_floor)
    score = max(score, settings.confidence_min_answered)
    score = round(min(score, 100.0))
    return score, level_for_score(score)


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