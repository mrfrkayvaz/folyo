import asyncio
import json
import httpx

from ..core.config import get_settings
from ..core.constants import SYSTEM_PROMPT
from .embeddings import AIError


def _auth(settings) -> tuple[str, str]:
    if not settings.llm_api_key or not settings.llm_base_url:
        raise AIError(
            "LLM ayarları eksik. web-api/.env dosyasına LLM_BASE_URL adresini ve API anahtarını (LLM_API_KEY) yazın."
        )
    if not settings.llm_model:
        raise AIError("LLM ayarları eksik. web-api/.env dosyasında LLM_MODEL tanımsız.")
    return settings.llm_api_key, settings.llm_base_url.rstrip("/")


async def stream_deltas(context_blocks: list[dict], question: str, on_delta):
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
        "include_reasoning": False,
        "stream": True,
        "temperature": settings.temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=None) as client:
        for attempt in range(1, 4):
            try:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code in (429, 502, 503) and attempt < 3:
                        await asyncio.sleep(attempt * 1.5)
                        continue
                    if resp.status_code == 401:
                        raise AIError("LLM: API anahtarı geçersiz (401). web-api/.env'i kontrol edin.")
                    if resp.status_code == 404:
                        raise AIError(f"LLM: model bulunamadı (404) — '{settings.llm_model}'.")
                    if resp.status_code == 429:
                        raise AIError("LLM: İstek limiti aşıldı (429). Lütfen birkaç saniye sonra tekrar deneyin.")
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
                        if "error" in obj:
                            err_detail = obj["error"]
                            err_msg = err_detail.get("message") if isinstance(err_detail, dict) else str(err_detail)
                            raise AIError(f"LLM hatası: {err_msg}")
                        choices = obj.get("choices") or []
                        if not choices:
                            continue
                        d_obj = choices[0].get("delta") or {}
                        text = d_obj.get("content") or d_obj.get("reasoning") or d_obj.get("text")
                        if text:
                            on_delta(text)
                return
            except httpx.HTTPStatusError as exc:
                if attempt == 3:
                    raise AIError(f"LLM servisi yanıt vermedi: {exc.response.status_code}") from exc
            except (httpx.TransportError, httpx.RequestError) as exc:
                if attempt == 3:
                    raise AIError(f"LLM sunucusuna bağlanılamadı: {exc}") from exc
