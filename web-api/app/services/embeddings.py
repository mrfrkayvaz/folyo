import asyncio

import numpy as np

from ..core.config import get_settings
from . import ai

BATCH_SIZE = 64

# Embedding batch çağrıları paralel akar ama sağlayıcıyı boğmamak için tavan sınırlıdır.
_EMBED_SEM = asyncio.Semaphore(max(1, int(get_settings().embed_max_concurrency)))


def _auth(settings) -> tuple[str, str]:
    api_key = settings.embed_api_key or settings.llm_api_key
    base = settings.embed_base_url or settings.llm_base_url
    base = ai.resolve(
        base_url=base,
        api_key=api_key,
        model=settings.embed_model,
        subject="Embedding",
        hint=" web-api/.env dosyasına LLM_BASE_URL (veya EMBED_BASE_URL) ve API anahtarını yazın.",
    )
    return api_key, base


async def embed_texts(texts: list[str], progress=None) -> np.ndarray:
    if not texts:
        raise ValueError("Embed edilecek metin yok.")

    settings = get_settings()
    api_key, base = _auth(settings)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def _one(offset: int, part: list[str]) -> tuple[int, list[list[float]]]:
        async with _EMBED_SEM:
            data = await ai.post_json(
                url=f"{base}/embeddings",
                headers=headers,
                payload={"model": settings.embed_model, "input": part},
                model=settings.embed_model,
                subject="Embedding",
                timeout=300,
            )
        items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        return offset, [item["embedding"] for item in items]

    batches = [(start, texts[start : start + BATCH_SIZE]) for start in range(0, len(texts), BATCH_SIZE)]
    # Batch'ler paralel; per-batch sıra deterministik (offset'e göre yeniden sıralanır).
    results = await asyncio.gather(*(_one(start, part) for start, part in batches))
    results.sort(key=lambda r: r[0])

    vectors = [v for _, vs in results for v in vs]
    if progress:
        for start, vs in results:
            done = start + len(vs)
            res = progress(done)
            if asyncio.iscoroutine(res):
                await res

    if not vectors:
        raise ai.AIError("Embedding servisi boş yanıt döndü.")

    dim = len(vectors[0])
    return np.asarray(vectors, dtype=np.float32).reshape(len(vectors), dim)