"""PDF ayrıştırma: sayfa içeriği, gömülü görseller, taranmış sayfa fallback."""

import io

import pymupdf
from PIL import Image

from ...core.config import get_settings
from ...core.enums import ContentType
from ..types import Segment
from . import blocks, images, layout
from .constants import (
    HEADER_FOOTER_RATIO,
    PAGE_CONTEXT_CHARS,
    PIXMAP_ZOOM,
)
from .errors import ExtractError


async def pdf_segments(content: bytes, crop_dir=None) -> list[Segment]:
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ExtractError(f"PDF okunamadı: {exc}") from exc

    try:
        segments: list[Segment] = []
        for pno in range(doc.page_count):
            segments.extend(await page_segments(doc[pno], pno + 1, crop_dir))
    finally:
        doc.close()

    if not segments:
        raise ExtractError("PDF'de çıkarılabilir içerik bulunamadı.")
    return segments


async def page_segments(page, page_number: int, crop_dir=None) -> list[Segment]:
    settings = get_settings()
    rect = page.rect
    top = rect.y0 + rect.height * HEADER_FOOTER_RATIO
    bottom = rect.y1 - rect.height * HEADER_FOOTER_RATIO

    table_list = _tables(page)
    block_data = page.get_text("dict").get("blocks", [])
    items = blocks.collect_items(block_data, table_list, top, bottom)

    if not items:
        if not _embedded_images(page):
            return []
        return [await scan_segment(page, page_number, rect)]

    items = await _image_items(page, rect, settings, items, crop_dir, page_number)
    ordered = layout.order_blocks(items, rect.width, rect.height)
    return layout.emit_segments(ordered, page_number, layout.body_font_size(items))


async def scan_segment(page, page_number: int, rect) -> Segment:
    """Sayfada metin/tablo yoksa tüm sayfayı görsel olarak işle."""
    settings = get_settings()
    pix = page.get_pixmap(matrix=pymupdf.Matrix(PIXMAP_ZOOM, PIXMAP_ZOOM))
    ctype, text, kind = await images.process_image(
        pix.tobytes("png"), settings, classify=False, fail_on_vision_missing=True
    )
    return Segment(
        content_type=ctype,
        text=text,
        page_number=page_number,
        bbox=[(rect.x0, rect.y0, rect.x1, rect.y1)],
        page_context=text[:PAGE_CONTEXT_CHARS],
        image_kind=kind,
    )


def _tables(page) -> list:
    try:
        return list(page.find_tables().tables or [])
    except Exception:
        return []


def _embedded_images(page) -> list:
    try:
        return list(page.get_images(full=True) or [])
    except Exception:
        return []


async def _image_items(page, rect, settings, items: list[dict], crop_dir, page_number: int) -> list[dict]:
    """Gömülü görselleri işler, kırpımları kaydeder ve item listesine ekler."""
    idx = 0
    for bbox, png in _embedded_image_streams(page, rect, settings):
        processed = await images.process_image(png, settings, classify=True, fail_on_vision_missing=False)
        if processed is None:
            continue
        ctype, text, kind = processed
        image_path = ""
        if crop_dir:
            idx += 1
            name = f"p{page_number}_i{idx}.png"
            crop_dir.mkdir(parents=True, exist_ok=True)
            (crop_dir / name).write_bytes(png)
            image_path = name
        items.append(
            {
                "kind": "image",
                "bbox": bbox,
                "text": text,
                "ctype": ctype,
                "image_path": image_path,
                "image_kind": kind,
            }
        )
    return items


def _embedded_image_streams(page, rect, settings):
    """Büyük gömülü görseller için `(bbox, png_bytes)` üretir (tekrar eden xref atlanır)."""
    seen: set[int] = set()
    for info in _embedded_images(page):
        xref = info[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if not rects:
            continue
        r = rects[0]
        w, h = r.width, r.height
        if min(w, h) < settings.image_min_px:
            continue
        big = max(w, h) >= settings.image_min_side_px or (
            w * h >= rect.width * rect.height * settings.image_min_area_ratio
        )
        if not big:
            continue
        try:
            raw = page.parent.extract_image(xref)
        except Exception:
            continue
        b = raw.get("image")
        if not b:
            continue
        try:
            with Image.open(io.BytesIO(b)) as im:
                buf = io.BytesIO()
                im.convert("RGB").save(buf, format="PNG")
                png = buf.getvalue()
        except Exception:
            png = b
        yield (r.x0, r.y0, r.x1, r.y1), png