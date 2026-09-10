import asyncio

import numpy as np

from ..core.config import get_settings
from . import ai

BATCH_SIZE = 64


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

    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        part = texts[start : start + BATCH_SIZE]
        data = await ai.post_json(
            url=f"{base}/embeddings",
            headers=headers,
            payload={"model": settings.embed_model, "input": part},
            model=settings.embed_model,
            subject="Embedding",
            timeout=300,
        )
        items = data.get("data", [])
        items.sort(key=lambda d: d.get("index", 0))
        for item in items:
            vectors.append(item["embedding"])
        if progress:
            res = progress(start + len(items))
            if asyncio.iscoroutine(res):
                await res

    if not vectors:
        raise ai.AIError("Embedding servisi boş yanıt döndü.")

    dim = len(vectors[0])
    return np.asarray(vectors, dtype=np.float32).reshape(len(vectors), dim)