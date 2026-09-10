"""Belge ayrıştırma: digital metin + tablo (PyMuPDF), OCR (Tesseract) ve Vision fallback."""

import io
from collections import Counter
from pathlib import Path
from typing import Union

import anyio
import pymupdf
from PIL import Image

from ..core.config import get_settings
from ..core.enums import ContentType
from . import ocr, vision
from .types import Segment

PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEXT_EXTS = {".txt", ".md"}

HEADER_FOOTER_RATIO = 0.07
MIN_COLUMN_GAP = 12.0
MIN_COLUMN_GAP_RATIO = 0.04
MIN_ROW_GAP = 8.0
MIN_ROW_GAP_RATIO = 0.008
MAX_CUT_DEPTH = 8
PAGE_CONTEXT_CHARS = 200
HEADING_SIZE_RATIO = 1.15
HEADING_MAX_CHARS = 120
HEADING_STACK = 3
_PIXMAP_ZOOM = 2.0


class ExtractError(Exception):
    pass


async def extract_segments(filename: str, source: Union[bytes, Path]) -> list[Segment]:
    content = source.read_bytes() if isinstance(source, Path) else source
    ext = Path(filename).suffix.lower()

    if ext in PDF_EXTS:
        return await _pdf_segments(content)

    if ext in TEXT_EXTS:
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

    if ext in IMAGE_EXTS:
        return await _image_segments(content)

    raise ExtractError(
        f"Desteklenmeyen dosya türü: '{ext or '(uzantı yok)'}'. Desteklenen: PDF, JPG, PNG, TXT, MD."
    )


async def _image_segments(content: bytes) -> list[Segment]:
    settings = get_settings()
    ctype, text = await _process_image(content, settings, classify=True, fail_on_vision_missing=True)
    return [
        Segment(
            content_type=ctype,
            text=text,
            page_number=1,
            page_context=text[:PAGE_CONTEXT_CHARS],
        )
    ]


async def _pdf_segments(content: bytes) -> list[Segment]:
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ExtractError(f"PDF okunamadı: {exc}") from exc

    try:
        segments: list[Segment] = []
        for pno in range(doc.page_count):
            segments.extend(await _page_segments(doc[pno], pno + 1))
    finally:
        doc.close()

    if not segments:
        raise ExtractError("PDF'de çıkarılabilir içerik bulunamadı.")
    return segments


async def _page_segments(page, page_number: int) -> list[Segment]:
    settings = get_settings()
    rect = page.rect
    top = rect.y0 + rect.height * HEADER_FOOTER_RATIO
    bottom = rect.y1 - rect.height * HEADER_FOOTER_RATIO

    tables = []
    try:
        tables = list(page.find_tables().tables or [])
    except Exception:
        tables = []

    items: list[dict] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        bx0, by0, bx1, by1 = block["bbox"]
        if by1 < top or by0 > bottom:
            continue
        if _overlaps_table(block["bbox"], tables):
            continue

        parts: list[str] = []
        sizes: list[float] = []
        bold = False
        for line in block.get("lines", []):
            line_text = "".join(sp.get("text", "") for sp in line.get("spans", []))
            parts.append(line_text)
            for sp in line.get("spans", []):
                if sp.get("text", "").strip():
                    sizes.append(float(sp.get("size", 0)))
                    if sp.get("flags", 0) & 16:
                        bold = True
        text = "\n".join(p for p in parts if p).strip()
        if not text:
            continue
        items.append(
            {
                "kind": "text",
                "bbox": (float(bx0), float(by0), float(bx1), float(by1)),
                "text": text,
                "size": max(sizes) if sizes else 0.0,
                "bold": bold,
            }
        )

    for t in tables:
        try:
            md = _table_to_markdown(t)
        except Exception:
            md = ""
        if not md:
            continue
        tb = t.bbox
        items.append(
            {
                "kind": "table",
                "bbox": (tb[0], tb[1], tb[2], tb[3]),
                "text": md,
                "ctype": ContentType.table.value,
            }
        )

    if not items:
        try:
            embedded = page.get_images(full=True) or []
        except Exception:
            embedded = []
        if not embedded:
            return []
        return [await _page_scan_segment(page, page_number, rect)]

    for bbox, png in _embedded_images(page, rect, settings):
        processed = await _process_image(png, settings, classify=True, fail_on_vision_missing=False)
        if processed is None:
            continue
        ctype, text = processed
        items.append({"kind": "image", "bbox": bbox, "text": text, "ctype": ctype})

    ordered = _order_blocks(items, rect.width, rect.height)
    return _emit_segments(ordered, page_number, _body_font_size(items))


async def _page_scan_segment(page, page_number: int, rect) -> Segment:
    settings = get_settings()
    pix = page.get_pixmap(matrix=pymupdf.Matrix(_PIXMAP_ZOOM, _PIXMAP_ZOOM))
    ctype, text = await _process_image(pix.tobytes("png"), settings, classify=False, fail_on_vision_missing=True)
    return Segment(
        content_type=ctype,
        text=text,
        page_number=page_number,
        bbox=[(rect.x0, rect.y0, rect.x1, rect.y1)],
        page_context=text[:PAGE_CONTEXT_CHARS],
    )


async def _process_image(
    image_bytes: bytes,
    settings,
    *,
    classify: bool,
    fail_on_vision_missing: bool,
) -> tuple[str, str] | None:
    stats = await anyio.to_thread.run_sync(ocr.ocr_image, image_bytes)
    if ocr.is_mostly_text(stats, settings):
        return ContentType.ocr_text.value, stats["text"]

    if not settings.vision_ready:
        if fail_on_vision_missing:
            raise ExtractError(
                "Görsel metin yoğunluğu düşük ve VISION_MODEL tanımlı değil. "
                "web-api/.env dosyasına VISION_API_KEY + VISION_BASE_URL + VISION_MODEL ekleyin."
            )
        return None

    if classify:
        return await vision.classify_and_describe(image_bytes)
    return ContentType.scanned_page.value, await vision.describe_image(image_bytes, "scanned_page")


def _embedded_images(page, rect, settings) -> list[tuple[tuple[float, float, float, float], bytes]]:
    out: list[tuple[tuple[float, float, float, float], bytes]] = []
    try:
        infos = page.get_images(full=True) or []
    except Exception:
        return out

    seen: set[int] = set()
    for info in infos:
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
        out.append(((r.x0, r.y0, r.x1, r.y1), png))
    return out


def _emit_segments(ordered: list[dict], page_number: int, body_size: float) -> list[Segment]:
    fallback_ctx = " ".join(it["text"] for it in ordered if it["kind"] == "text")[:PAGE_CONTEXT_CHARS]
    headings: list[tuple[str, float]] = []
    last_heading_size = 0.0

    def ctx() -> str:
        if headings:
            return " | ".join(h[0] for h in headings)
        return fallback_ctx

    segments: list[Segment] = []
    for order, it in enumerate(ordered):
        if it["kind"] != "text":
            segments.append(
                Segment(
                    content_type=it["ctype"],
                    text=it["text"],
                    page_number=page_number,
                    bbox=[it["bbox"]],
                    order=order,
                    page_context=ctx(),
                )
            )
            continue

        text, size, bold = it["text"], it["size"], it["bold"]
        threshold = max(body_size * HEADING_SIZE_RATIO, body_size + 1.0)
        if (size >= threshold or (bold and size > body_size)) and len(text) <= HEADING_MAX_CHARS:
            clean = text.replace("\n", " ")
            if headings and size >= last_heading_size * 0.85:
                headings[-1] = (clean, size)
            else:
                headings.append((clean, size))
                if len(headings) > HEADING_STACK:
                    headings.pop(0)
            last_heading_size = size

        segments.append(
            Segment(
                content_type=ContentType.text.value,
                text=text,
                page_number=page_number,
                bbox=[it["bbox"]],
                order=order,
                page_context=ctx(),
            )
        )
    return segments


def _body_font_size(items: list[dict]) -> float:
    sizes = [it["size"] for it in items if it["kind"] == "text" and it["size"] >= 4]
    if not sizes:
        return 11.0
    counts = Counter(sizes)
    best = max(counts.values())
    return min(s for s, c in counts.items() if c == best)


def _overlaps_table(bbox, tables) -> bool:
    bx0, by0, bx1, by1 = bbox
    barea = max(bx1 - bx0, 0) * max(by1 - by0, 0)
    if barea <= 0:
        return False
    for t in tables:
        tb = t.bbox
        ix0, iy0 = max(bx0, tb[0]), max(by0, tb[1])
        ix1, iy1 = min(bx1, tb[2]), min(by1, tb[3])
        if max(ix1 - ix0, 0) * max(iy1 - iy0, 0) / barea > 0.5:
            return True
    return False


def _table_to_markdown(table) -> str:
    rows = table.extract()
    if not rows:
        return ""
    rows = [
        [(c or "").replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip() for c in row]
        for row in rows
    ]
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    header = rows[0]
    md = "| " + " | ".join(header) + " |\n"
    md += "| " + " | ".join("---" for _ in header) + " |\n"
    for r in rows[1:]:
        md += "| " + " | ".join(r) + " |\n"
    return md.strip()


def _order_blocks(blocks: list[dict], width: float, height: float, depth: int = 0) -> list[dict]:
    if len(blocks) <= 1 or depth >= MAX_CUT_DEPTH:
        return sorted(blocks, key=lambda b: (round(b["bbox"][1]), b["bbox"][0]))

    x_gap = _largest_gap(blocks, 0)
    y_gap = _largest_gap(blocks, 1)

    if x_gap and x_gap[0] >= max(MIN_COLUMN_GAP, width * MIN_COLUMN_GAP_RATIO):
        cut = x_gap[1]
        left = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 < cut]
        right = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 >= cut]
        if len(left) >= 2 and len(right) >= 2:
            return _order_blocks(left, width, height, depth + 1) + _order_blocks(
                right, width, height, depth + 1
            )

    if y_gap and y_gap[0] >= max(MIN_ROW_GAP, height * MIN_ROW_GAP_RATIO):
        cut = y_gap[1]
        upper = [b for b in blocks if (b["bbox"][1] + b["bbox"][3]) / 2 < cut]
        lower = [b for b in blocks if (b["bbox"][1] + b["bbox"][3]) / 2 >= cut]
        if upper and lower:
            return _order_blocks(upper, width, height, depth + 1) + _order_blocks(
                lower, width, height, depth + 1
            )

    return sorted(blocks, key=lambda b: (round(b["bbox"][1]), b["bbox"][0]))


def _largest_gap(blocks: list[dict], axis: int) -> tuple[float, float] | None:
    intervals = sorted((b["bbox"][axis], b["bbox"][axis + 2]) for b in blocks)
    if len(intervals) < 2:
        return None
    max_end = intervals[0][1]
    best: tuple[float, float] | None = None
    for start, end in intervals[1:]:
        gap = start - max_end
        if gap > 0 and (best is None or gap > best[0]):
            best = (gap, (max_end + start) / 2)
        max_end = max(max_end, end)
    return best