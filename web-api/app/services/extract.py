"""Belgelerden metin çıkarma.

Şu an: PDF metin katmanı + düz metin dosyaları.
Görseller: OCR motoru kararı bekleniyor (arch.md §3.3) — 3.3 kararı gelince
bu dosyaya takılır, çağıran kod değişmez.
"""

import io
from pathlib import Path
from typing import Union

from pypdf import PdfReader

PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEXT_EXTS = {".txt", ".md"}


class ExtractError(Exception):
    """Belgeden metin çıkarılamadı — kullanıcıya gösterilecek Türkçe mesaj."""


def extract_text(filename: str, source: Union[bytes, Path]) -> str:
    """source: ham bayt VEYA diskte kayıtlı dosyanın yolu (depodan çekilirken path verilir)."""
    content = source.read_bytes() if isinstance(source, Path) else source
    ext = Path(filename).suffix.lower()
    if ext in PDF_EXTS:
        return _pdf(content)
    if ext in IMAGE_EXTS:
        raise ExtractError(
            "Görsel/OCR desteği henüz eklenmedi (arch.md §3.3 OCR kararı bekleniyor). "
            "Şimdilik PDF (metin katmanı) veya .txt/.md yükleyin."
        )
    if ext in TEXT_EXTS:
        return content.decode("utf-8", errors="replace")
    raise ExtractError(
        f"Desteklenmeyen dosya türü: '{ext or '(uzantı yok)'}'. "
        "Desteklenen: PDF, TXT, MD (görseller OCR sonrası)."
    )


def _pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:  # bozuk/şifreli PDF
        raise ExtractError(f"PDF okunamadı: {exc}") from exc
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # tek sayfa sorunluysa atla
            text = ""
        if text.strip():
            pages.append(text)
        elif not reader.pages:
            break
    text = "\n\n".join(pages).strip()
    if not text:
        raise ExtractError(
            "PDF'de metin katmanı bulunamadı (taranmış PDF). "
            "OCR desteği arch.md §3.3 kararıyla eklenecek."
        )
    return text
