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


async def embed_batches(texts: list[str], *, on_batch=None, progress=None) -> None:
    """Batch'leri paralel çeker ve **akışla** tüketir.

    Her tamamlanan batch `on_batch(offset, vectors)` ile çağırana teslim edilir
    (çağıran Chroma'ya yazar vb.) — tüm vektörler RAM'de birikmez. Sıra
    deterministik değildir (hangi batch önce biterse o), idempoten yazma buna izin verir.
    """
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
    tasks = [asyncio.create_task(_one(start, part)) for start, part in batches]

    done = 0
    for fut in asyncio.as_completed(tasks):
        offset, vecs = await fut
        if on_batch is not None:
            res = on_batch(offset, vecs)
            if asyncio.iscoroutine(res):
                await res
        done = max(done, offset + len(vecs))
        if progress:
            res = progress(done)
            if asyncio.iscoroutine(res):
                await res


async def embed_texts(texts: list[str], progress=None) -> np.ndarray:
    """Tüm metinleri embed edip tek matris döndürür (sorgu vektörleri gibi küçük kullanım).

    Büyük kullanımlar (belge embed) için `embed_batches` + akışlı Chroma yazımı tercih edilir.
    """
    collected: dict[int, list[list[float]]] = {}

    async def _collect(offset: int, vecs: list[list[float]]) -> None:
        collected[offset] = vecs

    await embed_batches(texts, on_batch=_collect, progress=progress)

    if not collected:
        raise ai.AIError("Embedding servisi boş yanıt döndü.")
    vectors = [v for offset in sorted(collected) for v in collected[offset]]
    if not vectors:
        raise ai.AIError("Embedding servisi boş yanıt döndü.")

    dim = len(vectors[0])
    return np.asarray(vectors, dtype=np.float32).reshape(len(vectors), dim)