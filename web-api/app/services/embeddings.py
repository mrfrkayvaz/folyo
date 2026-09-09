import asyncio
import httpx
import numpy as np

from ..core.config import get_settings


class AIError(Exception):
    pass


def _auth(settings) -> tuple[str, str]:
    api_key = settings.embed_api_key or settings.llm_api_key
    base = settings.embed_base_url or settings.llm_base_url
    if not api_key or not base:
        raise AIError(
            "Embedding ayarları eksik. web-api/.env dosyasına LLM_BASE_URL (veya EMBED_BASE_URL) ve API anahtarını yazın."
        )
    if not settings.embed_model:
        raise AIError("Embedding ayarları eksik. web-api/.env dosyasında EMBED_MODEL tanımsız.")
    return api_key, base.rstrip("/")


async def embed_texts(texts: list[str], progress=None) -> np.ndarray:
    if not texts:
        raise ValueError("Embed edilecek metin yok.")

    settings = get_settings()
    api_key, base = _auth(settings)
    url = f"{base}/embeddings"

    vectors: list[list[float]] = []
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    batch = 64

    async with httpx.AsyncClient(timeout=300) as client:
        for start in range(0, len(texts), batch):
            part = texts[start : start + batch]
            resp = None
            for attempt in range(1, 4):
                try:
                    resp = await client.post(
                        url,
                        json={"model": settings.embed_model, "input": part},
                        headers=headers,
                    )
                    if resp.status_code in (429, 502, 503) and attempt < 3:
                        await asyncio.sleep(attempt * 1.5)
                        continue
                    break
                except (httpx.RequestError, httpx.HTTPStatusError):
                    if attempt < 3:
                        await asyncio.sleep(attempt * 1.5)
                        continue
                    raise

            if resp is None:
                raise AIError("Embedding: Sunucudan yanıt alınamadı.")
            if resp.status_code == 401:
                raise AIError("Embedding: API anahtarı geçersiz (401). web-api/.env'i kontrol edin.")
            if resp.status_code == 404:
                raise AIError(f"Embedding: model bulunamadı (404) — '{settings.embed_model}'.")
            if resp.status_code == 429:
                raise AIError("Embedding: İstek limiti aşıldı (429). Lütfen birkaç saniye sonra tekrar deneyin.")

            resp.raise_for_status()
            data = resp.json().get("data", [])
            data.sort(key=lambda d: d.get("index", 0))
            for item in data:
                vectors.append(item["embedding"])
            if progress:
                progress(start + len(data))

    if not vectors:
        raise AIError("Embedding servisi boş yanıt döndü.")

    dim = len(vectors[0])
    return np.asarray(vectors, dtype=np.float32).reshape(len(vectors), dim)
