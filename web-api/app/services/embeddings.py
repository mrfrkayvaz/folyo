"""Embedding istemcisi — NVIDIA Nemotron 3 Embed 1B (OpenAI uyumlu /embeddings).

.env'de EMBED_MODEL/EMBED_* tanımlı; anahtar/base URL boşsa LLM_* alanlarına düşer.
"""

import httpx
import numpy as np

from ..config import get_settings


class AIError(Exception):
    """Kullanıcıya gösterilecek, yapılandırma/sağlayıcı kaynaklı hata."""


def _auth(settings) -> tuple[str, str]:
    api_key = settings.embed_api_key or settings.llm_api_key
    base = settings.embed_base_url or settings.llm_base_url
    if not api_key or not base:
        raise AIError(
            "Embedding ayarları eksik. web-api/.env dosyasına sağlayıcının "
            "LLM_BASE_URL (veya EMBED_BASE_URL) adresini ve API anahtarını yazın."
        )
    if not settings.embed_model:
        raise AIError(
            "Embedding ayarları eksik. web-api/.env dosyasında EMBED_MODEL tanımsız — "
            "örnek: EMBED_MODEL=nvidia/nemotron-3-embed-1b:free"
        )
    return api_key, base.rstrip("/")


async def embed_texts(texts: list[str], progress=None) -> np.ndarray:
    """Metin listesini tek istekte (64'lü gruplar) vektöre çevirir → float32 (N, dim)."""
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
            resp = await client.post(
                url,
                json={"model": settings.embed_model, "input": part},
                headers=headers,
            )
            if resp.status_code == 401:
                raise AIError("Embedding: API anahtarı geçersiz (401). web-api/.env'i kontrol edin.")
            if resp.status_code == 404:
                raise AIError(
                    f"Embedding: model bulunamadı (404) — '{settings.embed_model}'. "
                    "OpenRouter'da çoğu embed model yalnızca ':free' varyantıyla çalışır "
                    "(örn. nvidia/nemotron-3-embed-1b:free). Tam kimliği .env'deki EMBED_MODEL'e yazın."
                )
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
