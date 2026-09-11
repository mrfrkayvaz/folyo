"""Belge ayrıştırma girişi: uzantıya göre PDF / metin / görsel dağıtımı."""

from pathlib import Path
from typing import Union

from ...core.enums import ContentType
from ..types import Segment
from .constants import IMAGE_EXTS, PAGE_CONTEXT_CHARS, PDF_EXTS, TEXT_EXTS
from .errors import ExtractError
from .images import image_segments
from .pdf import pdf_segments

__all__ = ["ExtractError", "extract_segments"]


async def extract_segments(
    filename: str,
    source: Union[bytes, Path],
    crop_dir: Path | None = None,
) -> list[Segment]:
    content = source.read_bytes() if isinstance(source, Path) else source
    ext = Path(filename).suffix.lower()

    if ext in PDF_EXTS:
        return await pdf_segments(content, crop_dir)

    if ext in TEXT_EXTS:
        return [_text_segment(content)]

    if ext in IMAGE_EXTS:
        return await image_segments(content)

    raise ExtractError(
        f"Desteklenmeyen dosya türü: '{ext or '(uzantı yok)'}'. Desteklenen: PDF, JPG, PNG, TXT, MD."
    )


def _text_segment(content: bytes) -> Segment:
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        raise ExtractError("Dosyada metin bulunamadı.")
    return Segment(
        content_type=ContentType.text.value,
        text=text,
        page_number=1,
        page_context=text[:PAGE_CONTEXT_CHARS],
    )