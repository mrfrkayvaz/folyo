"""Belge ayrıştırma girişi: uzantıya göre ilgili işleyiciye (handler) yönlendirir.

Her desteklenen uzantının nasıl ele alınacağı `_HANDLERS` kaydında tektir:
yeni bir tür eklemek = yeni bir handler + kayda ekleme. Allowlist
(`SUPPORTED_EXTS`) hem bu yönlendirmede hem de upload ön-doğrulamasında
kullanılır — tek kaynak, çift tanım yok.
"""

from pathlib import Path
from typing import Awaitable, Callable, Union

from shared.core import fs as core_fs
from shared.core.enums import ContentType
from shared.services.types import Segment
from shared.services.extract.constants import PAGE_CONTEXT_CHARS, SUPPORTED_EXTS
from .errors import ExtractError
from .images import image_segments
from .pdf import pdf_segments

__all__ = ["ExtractError", "SUPPORTED_EXTS", "extract_segments"]

Handler = Callable[..., Awaitable[list[Segment]]]


async def _text_segment(content: bytes, crop_dir=None) -> list[Segment]:
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        raise ExtractError("Dosyada metin bulunamadı.")
    return [
        Segment(
            content_type=ContentType.text.value,
            text=text,
            page_number=1,
            page_context=text[:PAGE_CONTEXT_CHARS],
        )
    ]


# ── Ele alma mekanizması: uzantı → işleyici ───────────────────────────────
_HANDLERS: dict[str, Handler] = {
    ".pdf": pdf_segments,
    ".txt": _text_segment,
    ".md": _text_segment,
    ".png": image_segments,
    ".jpg": image_segments,
    ".jpeg": image_segments,
    ".webp": image_segments,
}


async def extract_segments(
    filename: str,
    source: Union[bytes, Path],
    crop_dir: Path | None = None,
) -> list[Segment]:
    content = await core_fs.read_bytes(source) if isinstance(source, Path) else source
    ext = Path(filename).suffix.lower()

    handler = _HANDLERS.get(ext)
    if handler is None:
        allowed = ", ".join(sorted(SUPPORTED_EXTS))
        raise ExtractError(
            f"Desteklenmeyen dosya türü: '{ext or '(uzantı yok)'}'. Desteklenen: {allowed}."
        )
    return await handler(content, crop_dir)