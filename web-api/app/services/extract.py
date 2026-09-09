import io
from pathlib import Path
from typing import Union

from pypdf import PdfReader

PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEXT_EXTS = {".txt", ".md"}


class ExtractError(Exception):
    pass


def extract_text(filename: str, source: Union[bytes, Path]) -> str:
    content = source.read_bytes() if isinstance(source, Path) else source
    ext = Path(filename).suffix.lower()

    if ext in PDF_EXTS:
        return _pdf(content)
    if ext in IMAGE_EXTS:
        raise ExtractError("Görsel/OCR desteği henüz eklenmedi. Şimdilik PDF veya .txt/.md yükleyin.")
    if ext in TEXT_EXTS:
        return content.decode("utf-8", errors="replace")

    raise ExtractError(f"Desteklenmeyen dosya türü: '{ext or '(uzantı yok)'}'. Desteklenen: PDF, TXT, MD.")


def _pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ExtractError(f"PDF okunamadı: {exc}") from exc

    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            pages.append(text)

    text = "\n\n".join(pages).strip()
    if not text:
        raise ExtractError("PDF'de metin katmanı bulunamadı.")
    return text
