"""DOCX metin çıkarımı — bağımsız: zipfile + ElementTree (yeni bağımlılık yok).

`word/document.xml` içindeki paragraf metin düğümlerini toplar; başlık/tablo/alt
yapılar MVP olarak okuma sırasında düz metin akışına indirilir.
"""

import io
import zipfile
import xml.etree.ElementTree as ET

from ...core.enums import ContentType
from ..types import Segment
from .constants import PAGE_CONTEXT_CHARS
from .errors import ExtractError

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_TAG_T = f"{{{_W_NS}}}t"
_TAG_P = f"{{{_W_NS}}}p"


async def docx_segments(content: bytes, crop_dir=None) -> list[Segment]:
    """DOCX → tek metin Segment'i (sayfa kavramı olmadığından page_number=1)."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            xml_bytes = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ExtractError(f"DOCX okunamadı: {exc}") from exc

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ExtractError(f"DOCX XML'i bozuk: {exc}") from exc

    paras: list[str] = []
    for p in root.iter(_TAG_P):
        text = "".join(t.text or "" for t in p.iter(_TAG_T)).strip()
        if text:
            paras.append(text)
    text = "\n".join(paras)
    if not text:
        raise ExtractError("DOCX içinde çıkarılabilir metin bulunamadı.")

    return [
        Segment(
            content_type=ContentType.text.value,
            text=text,
            page_number=1,
            page_context=text[:PAGE_CONTEXT_CHARS],
        )
    ]