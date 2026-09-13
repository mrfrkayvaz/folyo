import asyncio
import base64
from urllib.parse import urlparse

from ..core.config import get_settings
from shared.core.logging import get_logger
from shared.core.prompts import VISION_PROMPTS
from shared.services import ai

LOG = get_logger("vision")

_DEFAULT_MIME = "image/png"

# Yapılandırma özeti her süreçte bir kez loglanır (embed job başına tekrar etmez).
_CFG_LOGGED = False


def _base_host(base: str) -> str:
    """Log'a API key girmeden yalnızca host:kısım yazmak için."""
    parsed = urlparse(base)
    host = parsed.hostname or base
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return f"{host}{parsed.path}" if parsed.path else host

# Tüm Vision akışları (sayfa görselleri, denklem fallback'i, scanner) tek bir ortak
# eşzamanlılık sınırını paylaşır — paralel çalışır ama sağlayıcıya seri darbe yapmaz.
_VISION_SEM = asyncio.Semaphore(max(1, int(get_settings().vision_max_concurrency)))


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
    global _CFG_LOGGED
    if not _CFG_LOGGED:
        _CFG_LOGGED = True
        LOG.info(
            "[vision] YAPILANDIRMA: ready=%s api_key=%s base=%s model=%s "
            "(dedicated=%s, fallback_llm=%s)",
            settings.vision_ready,
            "VAR" if api_key else "YOK",
            _base_host(base),
            settings.vision_model,
            "evet" if settings.vision_api_key else "hayır",
            "evet" if not settings.vision_api_key and settings.llm_api_key else "hayır",
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

    LOG.info(
        "[vision] istek: görsel=%d B mime=%s model=%s detail=%s prompt=%r",
        len(image),
        mime,
        settings.vision_model,
        detail,
        (prompt or "")[:80],
    )

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

    # API çağrısı semafor içinde: yeniden denemeler de eşzamanlılık tavanını aşamaz.
    async with _VISION_SEM:
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
                LOG.error("[vision] API hata payload'ı (attempt %d): %s", attempt, msg)
                raise ai.AIError(f"Vision hatası: {msg}")

            choices = data.get("choices") or []
            content = (choices[0].get("message") or {}).get("content") if choices else None
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            text = (content or "").strip()
            if text:
                LOG.info("[vision] yanıt: attempt=%d metin=%d karakter", attempt, len(text))
                return text
            LOG.warning("[vision] attempt %d BOŞ içerik döndü — yeniden deneniyor", attempt)
            await asyncio.sleep(attempt * 1.5)

    LOG.warning("[vision] 3 deneme de boş içerik — AIError'la çıkılıyor")
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


async def describe_content(
    image: bytes,
    *,
    mime: str = _DEFAULT_MIME,
    detail: str = "auto",
    max_tokens: int = 1500,
) -> str:
    """Görseli metne döker: yazı içerikliyse yazıları çıkarır, değilse yorumlar."""
    return await analyze_image(
        image, VISION_PROMPTS["describe"], mime=mime, detail=detail, max_tokens=max_tokens
    )