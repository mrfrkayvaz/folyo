"""Belge işleme hattı: metin çıkar → parçala (chunk_text burada)."""

import re

from ..config import get_settings
from . import extract


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    """Paragraf korumalı basit parçalayıcı (karakter tabanlı, cümle kırmaz)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")
    text = "\n".join(" ".join(line.split()) for line in text.split("\n"))
    text = text.replace("\n \n", "\n\n")
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind("\n", start, end)
            if cut <= start + size * 0.5:
                cut = text.rfind(" ", start, end)
            if cut > start + size * 0.5:
                end = cut
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
        if start < n:
            nxt = text.find(" ", start, min(start + overlap, n))
            if nxt != -1 and nxt - start < overlap:
                start = nxt + 1

    if len(chunks) > 1 and len(chunks[-1]) < size * 0.3:
        chunks[-2] = f"{chunks[-2]}\n\n{chunks[-1]}"
        chunks.pop()
    return chunks


def extract_text_for(filename: str, path) -> str:
    """Diskteki dosyadan metin çıkar (extract modülüne kısa yol)."""
    return extract.extract_text(filename, path)