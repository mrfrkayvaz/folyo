"""Görsel işleme: OCR yoğunluk testi → Vision fallback.

Küçük bir görsel, `(content_type, text, image_kind)` üçlüsüne dönüştürülür:

- OCR "çoğu yazıdan oluşuyor" derse → tip `ocr_text`, detay yok.
- Değilse Vision LLM görseli metne döker → tip `image`.
- Vision yoksa ve zorunlu değilse `None` (görsel atlanır).
"""

import asyncio

import anyio

from ...core.config import get_settings
from ...core.enums import ContentType
from ..types import Segment
from .. import ocr, vision
from .constants import PAGE_CONTEXT_CHARS

# OCR (Tesseract) CPU işidir: görsel işleme paralel akar ama Tesseract yarışı
# sınırlanır (CPU boğulması / thread güvenliği).
_OCR_SEM = asyncio.Semaphore(max(1, int(get_settings().ocr_max_concurrency)))
from .errors import ExtractError


def is_diagram_like(stats: dict, settings) -> bool:
    """OCR metni kabul edilebilir olsa bile yoğunluk çok düşükse diyagram/infografiktir:
    büyük resimde az ve dağınık sözcük → tip `image` (görsel korunur, Vision çağrısı yok)."""
    return (
        stats["word_count"] < settings.ocr_diagram_max_words
        and stats["text_coverage"] < settings.ocr_diagram_max_coverage
    )


async def process_image(
    image_bytes: bytes,
    settings,
    *,
    classify: bool,
    fail_on_vision_missing: bool,
) -> tuple[str, str, str] | None:
    """Görselden `(content_type, text, image_kind)` üretir; kabul edilmezse `None`."""
    stats = None
    async with _OCR_SEM:
        stats = await anyio.to_thread.run_sync(ocr.ocr_image, image_bytes)
    if ocr.is_mostly_text(stats, settings):
        if is_diagram_like(stats, settings):
            # Dağınık etiketli diyagram: OCR çıktısı içerik olarak kalır ama görsel tipinde
            # chunk üretilir — hem aranabilir (OCR sözcükleri) hem de placeholder ile gösterilir.
            return ContentType.image.value, stats["text"], "diagram"
        return ContentType.ocr_text.value, stats["text"], ""

    if not settings.vision_ready:
        if fail_on_vision_missing:
            raise ExtractError(
                "Görsel metin yoğunluğu düşük ve VISION_MODEL tanımlı değil. "
                "web-api/.env dosyasına VISION_API_KEY + VISION_BASE_URL + VISION_MODEL ekleyin."
            )
        return None

    if classify:
        text = await vision.describe_content(image_bytes)
        return ContentType.image.value, text, ""

    text = await vision.describe_image(image_bytes, "scanned_page")
    return ContentType.image.value, text, ""


async def image_segments(content: bytes, crop_dir=None) -> list[Segment]:
    """Tek başına yüklenen görsel dosyası → tek Segment."""
    settings = get_settings()
    ctype, text, kind = await process_image(content, settings, classify=True, fail_on_vision_missing=True)
    return [
        Segment(
            content_type=ctype,
            text=text,
            page_number=1,
            page_context=text[:PAGE_CONTEXT_CHARS],
            image_kind=kind,
        )
    ]