import asyncio
import base64

from ..core.config import get_settings
from ..core.enums import ImageKind
from ..core.prompts import VISION_PROMPTS
from . import ai

_DEFAULT_MIME = "image/png"

# Vision modelinin söylediği görsel türü → metadata detayı (image_kind).
IMAGE_KIND_BY_TIP = {
    "chart": ImageKind.image_caption.value,
    "grafik": ImageKind.image_caption.value,
    "diagram": ImageKind.diagram.value,
    "akis": ImageKind.diagram.value,
    "form": ImageKind.form_data.value,
    "fatura": ImageKind.form_data.value,
    "scan": ImageKind.scanned_page.value,
    "scanned": ImageKind.scanned_page.value,
    "photo": ImageKind.scanned_page.value,
    "foto": ImageKind.scanned_page.value,
}


def _auth(settings) -> tuple[str, str]:
    api_key = settings.vision_api_key or settings.llm_api_key
    base = settings.vision_base_url or settings.llm_base_url
    base = ai.resolve(
        base_url=base,
        api_key=api_key,
        model=settings.vision_model,
        subject="Vision",
        hint=" web-api/.env dosyasına VISION_BASE_URL ve VISION_API_KEY yazın.",
    )
    return api_key, base


def to_data_uri(image: bytes, mime: str = _DEFAULT_MIME) -> str:
    if not image:
        raise ai.AIError("Vision: boş görsel verisi.")
    return f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}"


async def analyze_image(
    image: bytes,
    prompt: str,
    *,
    mime: str = _DEFAULT_MIME,
    detail: str = "auto",
    max_tokens: int = 1500,
    temperature: float = 0.1,
) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("Vision: prompt boş olamaz.")

    settings = get_settings()
    api_key, base = _auth(settings)

    image_url: dict = {"url": to_data_uri(image, mime)}
    if detail:
        image_url["detail"] = detail

    payload = {
        "model": settings.vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": image_url},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for attempt in range(1, 4):
        data = await ai.post_json(
            url=f"{base}/chat/completions",
            headers=headers,
            payload=payload,
            model=settings.vision_model,
            subject="Vision",
        )
        error = data.get("error")
        if error:
            msg = error.get("message") if isinstance(error, dict) else str(error)
            raise ai.AIError(f"Vision hatası: {msg}")

        choices = data.get("choices") or []
        content = (choices[0].get("message") or {}).get("content") if choices else None
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        text = (content or "").strip()
        if text:
            return text
        await asyncio.sleep(attempt * 1.5)

    raise ai.AIError("Vision servisi boş içerik döndürdü.")


async def describe_image(
    image: bytes,
    purpose: str,
    *,
    mime: str = _DEFAULT_MIME,
    detail: str = "auto",
    max_tokens: int = 1500,
) -> str:
    prompt = VISION_PROMPTS.get(purpose)
    if not prompt:
        raise ValueError(f"Vision: bilinmeyen amaç '{purpose}'. Geçerli: {', '.join(VISION_PROMPTS)}.")
    return await analyze_image(image, prompt, mime=mime, detail=detail, max_tokens=max_tokens)


async def classify_and_describe(
    image: bytes,
    *,
    mime: str = _DEFAULT_MIME,
    detail: str = "auto",
    max_tokens: int = 1500,
) -> tuple[str, str]:
    """Görseli sınıflandırıp betimler; `(image_kind, text)` döndürür."""
    raw = await analyze_image(
        image, VISION_PROMPTS["classify_image"], mime=mime, detail=detail, max_tokens=max_tokens
    )
    lines = raw.strip().splitlines()
    head = (lines[0] if lines else "").lstrip().replace("İ", "i").lower()
    tip = "scan"
    content = raw.strip()
    if head.startswith(("tip:", "tür:", "type:")):
        tip = head.split(":", 1)[1].strip()
        rest = "\n".join(lines[1:]).strip()
        content = rest or content
    return IMAGE_KIND_BY_TIP.get(tip, ImageKind.scanned_page.value), content