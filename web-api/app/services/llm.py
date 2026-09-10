from ..core.config import get_settings
from ..core.constants import SYSTEM_PROMPT
from . import ai


def _auth(settings) -> tuple[str, str]:
    base = ai.resolve(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        subject="LLM",
        hint=" web-api/.env dosyasına LLM_BASE_URL adresini ve API anahtarını (LLM_API_KEY) yazın.",
    )
    return settings.llm_api_key, base


def _message(obj: dict) -> str:
    content = (obj.get("choices") or [{}])[0].get("message", {}).get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return (content or "").strip()


async def stream_deltas(context_blocks: list[dict], question: str, on_delta):
    settings = get_settings()
    api_key, base = _auth(settings)

    context = "\n\n".join(
        f"[{c['name']}, sayfa {c.get('page_number', 1)}, parça {c['chunk_index'] + 1}]\n{c['text']}"
        for c in context_blocks
    )
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"BAĞLAM (yüklenen belgelerden alıntılar):\n\n{context}\n\nKullanıcı sorusu: {question}",
            },
        ],
        "include_reasoning": False,
        "stream": True,
        "temperature": settings.temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async for obj in ai.stream_json(
        url=f"{base}/chat/completions",
        headers=headers,
        payload=payload,
        model=settings.llm_model,
        subject="LLM",
    ):
        error = obj.get("error")
        if error:
            msg = error.get("message") if isinstance(error, dict) else str(error)
            raise ai.AIError(f"LLM hatası: {msg}")
        choices = obj.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        text = delta.get("content") or delta.get("reasoning") or delta.get("text")
        if text:
            on_delta(text)


async def complete(messages: list[dict], *, temperature: float | None = None, max_tokens: int = 1024) -> str:
    settings = get_settings()
    api_key, base = _auth(settings)

    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": settings.temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = await ai.post_json(
        url=f"{base}/chat/completions",
        headers=headers,
        payload=payload,
        model=settings.llm_model,
        subject="LLM",
    )
    error = data.get("error")
    if error:
        msg = error.get("message") if isinstance(error, dict) else str(error)
        raise ai.AIError(f"LLM hatası: {msg}")
    text = _message(data)
    if not text:
        raise ai.AIError("LLM servisi boş içerik döndürdü.")
    return text