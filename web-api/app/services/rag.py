"""Retrieval + üretim hattı: workspace-scope'lu chroma sorgusu + streaming LLM.

Olay sözlükleri:
  {"type":"meta","sources":[{label,meta}]}  → başlangıçta kaynaklar
  {"type":"delta","text":...}               → token token içerik
  {"type":"done","sources":[...]}
  {"type":"error","message":...}
"""

import asyncio
import uuid

from ..config import get_settings
from . import chroma_store, embeddings, llm


async def qa_events(workspace_id: uuid.UUID, question: str):
    settings = get_settings()

    # 1) Soruyu vektöre çevir
    try:
        qvec = (await embeddings.embed_texts([question]))[0]
    except Exception as exc:
        yield {"type": "error", "message": f"Embedding hatası: {exc}"}
        return

    # 2) SADECE bu workspace'in belgelerinde ara
    hits = await chroma_store.query(workspace_id, qvec, settings.top_k)
    if not hits:
        yield {
            "type": "error",
            "message": "Bu sohbette henüz embedlenmiş belge yok. Bir belge yükleyip "
            "dizinlemenin bitmesini bekleyin, sonra sorunuzu sorun.",
        }
        return

    # 3) Kaynak özeti (benzersiz belgeler + kaç parça)
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

    # 4) LLM'i token token akıt (kuyruk üzerinden)
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