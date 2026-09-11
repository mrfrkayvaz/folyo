"""Görsel işleme: OCR yoğunluk testi → Vision fallback.

Küçük bir görsel, `(content_type, text, image_kind)` üçlüsüne dönüştürülür:

- OCR "çoğu yazıdan oluşuyor" derse → tip `ocr_text`, detay yok.
- Değilse Vision LLM devreye girer → tip `image`, detay `image_kind`
  (image_caption | diagram | form_data | scanned_page) metadata'ya yazılır.
- Vision yoksa ve zorunlu değilse `None` (görsel atlanır).
"""

import anyio

from ...core.config import get_settings
from ...core.enums import ContentType, ImageKind
from ..types import Segment
from .. import ocr, vision
from .constants import PAGE_CONTEXT_CHARS
from .errors import ExtractError


async def process_image(
    image_bytes: bytes,
    settings,
    *,
    classify: bool,
    fail_on_vision_missing: bool,
) -> tuple[str, str, str] | None:
    """Görselden `(content_type, text, image_kind)` üretir; kabul edilmezse `None`."""
    stats = await anyio.to_thread.run_sync(ocr.ocr_image, image_bytes)
    if ocr.is_mostly_text(stats, settings):
        return ContentType.ocr_text.value, stats["text"], ""

    if not settings.vision_ready:
        if fail_on_vision_missing:
            raise ExtractError(
                "Görsel metin yoğunluğu düşük ve VISION_MODEL tanımlı değil. "
                "web-api/.env dosyasına VISION_API_KEY + VISION_BASE_URL + VISION_MODEL ekleyin."
            )
        return None

    if classify:
        kind, text = await vision.classify_and_describe(image_bytes)
        return ContentType.image.value, text, kind

    kind = ImageKind.scanned_page.value
    return ContentType.image.value, await vision.describe_image(image_bytes, kind), kind


async def image_segments(content: bytes) -> list[Segment]:
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