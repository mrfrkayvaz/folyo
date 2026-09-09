"""LLM istemcisi — NVIDIA Nemotron 3 Ultra (OpenAI uyumlu /chat/completions, SSE akışı).

`stream_deltas` yanıtı token token üretir; main rota bunu istemciye SSE olarak iletir.
"""

import json

import httpx

from ..config import get_settings
from .embeddings import AIError

SYSTEM_PROMPT = (
    "Sen Contextus'sun: yüklenen belgelere dayalı soru-cevap yapan bir asistan."
    "Kesin kurallar:\n"
    "1. Yalnızca aşağıdaki BAĞLAM bölümündeki bilgileri kullan. Belgede olmayan hiçbir şeyi"
    " uydurma, tahmin etme veya dış bilgiyle doldurma.\n"
    "2. Sorunun cevabı bağlamda yoksa doğrudan şunu söyle: \"Bu bilgi belgede bulunmuyor.\""
    " ve kısa bir gerekçe ver; asla zorlama bir cevap üretme (hallucination guard).\n"
    "3. Cevap verirken kaynağa atıfta bulun: [BelgeAdı, parça N] şeklinde.\n"
    "4. Türkçe soruya Türkçe, İngilizce soruya İngilizce cevap ver.\n"
    "5. Kısa ve öz ol; liste kullanacaksan madde işaretleriyle yaz."
)


def _auth(settings) -> tuple[str, str]:
    if not settings.llm_api_key or not settings.llm_base_url:
        raise AIError(
            "LLM ayarları eksik. web-api/.env dosyasına LLM_BASE_URL adresini ve "
            "API anahtarını (LLM_API_KEY) yazın."
        )
    if not settings.llm_model:
        raise AIError(
            "LLM ayarları eksik. web-api/.env dosyasında LLM_MODEL tanımsız — "
            "örnek: LLM_MODEL=google/gemma-4-31b-it:free"
        )
    return settings.llm_api_key, settings.llm_base_url.rstrip("/")


async def stream_deltas(context_blocks: list[dict], question: str, on_delta):
    """context_blocks: retrieval sonucu [{name, doc_index, text}]. Token token çağırır."""
    settings = get_settings()
    api_key, base = _auth(settings)
    url = f"{base}/chat/completions"

    context = "\n\n".join(
        f"[{c['name']}, parça {c['doc_index'] + 1}]\n{c['text']}" for c in context_blocks
    )
    user_content = (
        f"BAĞLAM (yüklenen belgelerden alıntılar):\n\n{context}\n\n"
        f"Kullanıcı sorusu: {question}"
    )
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": True,
        "temperature": settings.temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code == 401:
                raise AIError("LLM: API anahtarı geçersiz (401). web-api/.env'i kontrol edin.")
            if resp.status_code == 404:
                raise AIError(
                    f"LLM: model bulunamadı (404) — '{settings.llm_model}'. "
                    "Sağlayıcıdaki tam model kimliğini .env'deki LLM_MODEL'e yazın."
                )
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    on_delta(delta)
