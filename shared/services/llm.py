import asyncio

from ..core.config import get_settings
from ..core.prompts import SYSTEM_PROMPT
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


def _context_label(c: dict) -> str:
    """Context block label: document, page, chunk (images add `image: doc_id/file_name`)."""
    parts = [c["name"], f"sayfa {c.get('page_number', 1)}", f"parça {c['chunk_index'] + 1}"]
    if c.get("content_type") == "image" and c.get("image_path"):
        parts.append(f"görsel: {c.get('doc_id', '?')}/{c['image_path']}")
    return "[" + ", ".join(parts) + "]"


def _user_content(context: str, question: str, context_blocks: list[dict]) -> str:
    """User message: context + available images + question."""
    content = f"CONTEXT (excerpts from uploaded documents):\n\n{context}"
    # The same image may appear in several chunks; list it once.
    avail = list(dict.fromkeys(
        f"[Görsel: {c.get('doc_id', '?')}/{c['image_path']}]"
        for c in context_blocks
        if c.get("content_type") == "image" and c.get("image_path")
    ))
    if avail:
        content += (
            "\n\nAVAILABLE IMAGES: "
            + ", ".join(avail)
            + "\nIf you used the content of one of these images, copy its [Görsel: ...] placeholder "
            + "verbatim from the list and place it at the single most relevant point (it is rendered "
            + "as a block image). Show each image only ONCE: even if several pieces of information "
            + "come from the same image, do not repeat the placeholder and do not write a "
            + "[Belge, sayfa, parça] atıf for it."
        )
    return f"{content}\n\nUser question: {question}"


async def stream_deltas(context_blocks: list[dict], question: str, on_delta):
    settings = get_settings()
    api_key, base = _auth(settings)

    def _context_block(c: dict) -> str:
        """Künye + (gerekirse) `[Bölüm: …]` ön cümlesi + metin.

        Chroma metinleri artık breadcrumb ön eki içermiyor (gürültüsüz embed); bölüm
        bilgisinin LLM bağlamına düşmemesi için metadata breadcrumbs'ından yeniden kurulur.
        """
        label = _context_label(c)
        text = c["text"]
        if not text.lstrip().startswith("[Section:"):
            crumbs = c.get("breadcrumbs") or []
            if crumbs:
                text = f"[Section: {' > '.join(crumbs)}]\n{text}"
        return f"{label}\n{text}"

    context = "\n\n".join(_context_block(c) for c in context_blocks)
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _user_content(context, question, context_blocks),
            },
        ],
        "include_reasoning": False,
        "stream": True,
        "temperature": settings.temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for attempt in range(1, 4):
        emitted = 0

        def emit(text: str) -> None:
            nonlocal emitted
            emitted += len(text)
            on_delta(text)

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
                emit(text)

        if emitted > 0:
            return
        await asyncio.sleep(attempt * 1.5)

    raise ai.AIError("LLM servisi boş içerik döndürdü.")


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

    for attempt in range(1, 4):
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
        if text:
            return text
        await asyncio.sleep(attempt * 1.5)

    raise ai.AIError("LLM servisi boş içerik döndürdü.")