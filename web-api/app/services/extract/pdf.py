"""PDF ayrıştırma: sayfa içeriği, gömülü görseller, taranmış sayfa fallback."""

import asyncio
import io
import math
from collections import Counter

import pymupdf
from PIL import Image

from ...core import fs as core_fs
from ...core.config import get_settings
from ...core.enums import ContentType
from ...core.logging import get_logger
from ..types import Segment
from . import blocks, equations, images, layout
from .constants import (
    HEADER_FOOTER_RATIO,
    PAGE_CONTEXT_CHARS,
    PIXMAP_ZOOM,
)
from .errors import ExtractError

LOG = get_logger("extract.pdf")

# Sabit başlık/altbilgi tespiti örnekleme bandı (dikey alanın üst/son yüzdesi).
REPEAT_SAMPLE_BAND = 0.10


def _norm_text(text: str) -> str:
    return " ".join(text.lower().split())


def _detect_repeats(pages, repeat_ratio: float) -> set[str]:
    """Üst/son %10 bandında sayfalar arası yinelenen metin kümesi (sabit başlık/altbilgi).

    (normalleştirilmiş metin, y-bandı) çifti sayfaların ≥ repeat_ratio kadarında görülüyorsa
    suppress listesine girer. Sayfa-bazlı değişen içerik (bölüm başlığı, madde numaraları vb.)
    tekrar etmediği için listede yer almaz.
    """
    counts: Counter[str] = Counter()
    n = len(pages)
    band = REPEAT_SAMPLE_BAND
    for page in pages:
        h = page.rect.height
        for b in page.get_text("blocks") or []:
            if len(b) <= 6 or b[6] != 0:  # type: 0 = metin bloğu
                continue
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if y1 <= h * band or y0 >= h * (1 - band):
                t = _norm_text(text)
                if len(t) >= 2 and any(ch.isalnum() for ch in t):
                    counts[t] += 1
    threshold = max(2, math.ceil(n * repeat_ratio)) if n else 0
    if not threshold:
        return set()
    return {t for t, c in counts.items() if c >= threshold}


async def pdf_segments(content: bytes, crop_dir=None) -> list[Segment]:
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ExtractError(f"PDF okunamadı: {exc}") from exc

    try:
        settings = get_settings()
        pages = [doc[pno] for pno in range(doc.page_count)]
        skip_repeats = _detect_repeats(pages, settings.header_footer_repeat_ratio)
        segments: list[Segment] = []
        for pno, page in enumerate(pages):
            segments.extend(await page_segments(page, pno + 1, crop_dir, skip=skip_repeats))
    finally:
        doc.close()

    if not segments:
        raise ExtractError("PDF'de çıkarılabilir içerik bulunamadı.")
    return segments


async def page_segments(
    page,
    page_number: int,
    crop_dir=None,
    skip: set[str] | None = None,
) -> list[Segment]:
    settings = get_settings()
    rect = page.rect
    top = rect.y0 + rect.height * HEADER_FOOTER_RATIO
    bottom = rect.y1 - rect.height * HEADER_FOOTER_RATIO
    skip_top = rect.y0 + rect.height * REPEAT_SAMPLE_BAND
    skip_bottom = rect.y1 - rect.height * REPEAT_SAMPLE_BAND

    table_list = _tables(page)
    block_data = page.get_text("dict").get("blocks", [])
    items = blocks.collect_items(
        block_data, table_list, top, bottom, skip, skip_top, skip_bottom, page_width=rect.width
    )

    if not items:
        if not _embedded_images(page):
            return []
        return [await scan_segment(page, page_number, rect)]

    items = await _image_items(page, rect, settings, items, crop_dir, page_number)
    await equations.vision_fixup(page, items, settings)
    textlike = [it for it in items if it["kind"] in ("text", "code", "equation")]
    anchors = [it for it in items if it["kind"] not in ("text", "code", "equation")]
    ordered = layout.inject_anchors(layout.order_blocks(textlike, rect.width, rect.height), anchors)
    return layout.emit_segments(ordered, page_number, layout.body_font_size(items))


async def scan_segment(page, page_number: int, rect) -> Segment:
    """Sayfada metin/tablo yoksa tüm sayfayı görsel olarak işle."""
    settings = get_settings()
    LOG.info("[pdf] sayfa %d TÜMÜ görsel (metin/tablo yok) → taranmış sayfa Vision akışı", page_number)
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
    """Gömülü görselleri işler (OCR/Vision **paralel**), kırpımları kaydeder, item listesine ekler.

    `process_image` çağrıları `gather` ile paralel akar; Vision tarafı global
    semaforla sınırlıdır. Item sırası (düzen için önemli) sabit kalır.
    """
    streams = list(_embedded_image_streams(page, rect, settings))
    if not streams:
        return items
    LOG.info("[pdf] sayfa %d: %d gömülü görsel adayı (OCR/Vision'a gidiyor)", page_number, len(streams))

    async def _process(bbox_png):
        bbox, png = bbox_png
        return await images.process_image(
            png, settings, classify=True, fail_on_vision_missing=False
        )

    processed_all = await asyncio.gather(*(_process(s) for s in streams))

    skipped = sum(1 for p in processed_all if p is None)
    if skipped:
        LOG.info("[pdf] sayfa %d: %d/%d görsel adayı ATLANDI (None döndü)", page_number, skipped, len(streams))

    idx = 0
    for (bbox, png), processed in zip(streams, processed_all):
        if processed is None:
            continue
        ctype, text, kind = processed
        image_path = ""
        if crop_dir:
            idx += 1
            name = f"p{page_number}_i{idx}.png"
            crop_dir.mkdir(parents=True, exist_ok=True)
            await core_fs.write_bytes(crop_dir / name, png)
            image_path = name
            LOG.info(
                "[pdf] kırpım kaydedildi: %s/%s (%d B, bbox=%s)",
                crop_dir,
                name,
                len(png),
                [round(v, 1) for v in bbox],
            )
        LOG.info(
            "[pdf] görsel item: ctype=%s kind=%s metin=%d karakter image_path=%r",
            ctype,
            kind,
            len(text or ""),
            image_path,
        )
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
            LOG.debug(
                "[pdf] xref %s atlandı: çok küçük (%.0fx%.0f < image_min_px=%d)",
                xref, w, h, settings.image_min_px,
            )
            continue
        big = max(w, h) >= settings.image_min_side_px or (
            w * h >= rect.width * rect.height * settings.image_min_area_ratio
        )
        if not big:
            LOG.debug(
                "[pdf] xref %s atlandı: büyük değil (%.0fx%.0f, min_side=%d, min_area_ratio=%.2f)",
                xref, w, h, settings.image_min_side_px, settings.image_min_area_ratio,
            )
            continue
        try:
            raw = page.parent.extract_image(xref)
        except Exception:
            LOG.debug("[pdf] xref %s extract_image başarısız", xref)
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