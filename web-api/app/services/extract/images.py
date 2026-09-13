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
from ...core.logging import get_logger
from ..types import Segment
from .. import ocr, vision
from .constants import PAGE_CONTEXT_CHARS

LOG = get_logger("extract.images")

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
    mostly_text = ocr.is_mostly_text(stats, settings)
    LOG.info(
        "[image] OCR: bytes=%d words=%d conf=%.1f coverage=%.3f alnum=%.3f mostly_text=%s",
        len(image_bytes),
        stats["word_count"],
        stats["mean_conf"],
        stats["text_coverage"],
        stats["alnum_ratio"],
        mostly_text,
    )
    if mostly_text:
        if is_diagram_like(stats, settings):
            LOG.info(
                "[image] karar=diagram: words=%d coverage=%.3f (OCR metni içerik olarak kalıyor, Vision yok)",
                stats["word_count"],
                stats["text_coverage"],
            )
            # Dağınık etiketli diyagram: OCR çıktısı içerik olarak kalır ama görsel tipinde
            # chunk üretilir — hem aranabilir (OCR sözcükleri) hem de placeholder ile gösterilir.
            return ContentType.image.value, stats["text"], "diagram"
        LOG.info("[image] karar=ocr_text")
        return ContentType.ocr_text.value, stats["text"], ""

    if not settings.vision_ready:
        LOG.warning(
            "[image] Vision HAZIR DEĞİL (ready=%s fail_on_vision_missing=%s): "
            "görsel SESSİZCE ATLANIYOR — görsel chunk üretilemez. "
            "Kontrol: VISION_API_KEY / VISION_BASE_URL / VISION_MODEL env'leri",
            settings.vision_ready,
            fail_on_vision_missing,
        )
        if fail_on_vision_missing:
            raise ExtractError(
                "Görsel metin yoğunluğu düşük ve VISION_MODEL tanımlı değil. "
                "web-api/.env dosyasına VISION_API_KEY + VISION_BASE_URL + VISION_MODEL ekleyin."
            )
        return None

    if classify:
        LOG.info("[image] Vision çağrısı: describe_content (classify=True)")
        text = await vision.describe_content(image_bytes)
    else:
        LOG.info("[image] Vision çağrısı: describe_image scanned_page (classify=False)")
        text = await vision.describe_image(image_bytes, "scanned_page")
    LOG.info("[image] Vision sonucu: ctype=image metin=%d karakter kind=''", len(text or ""))
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