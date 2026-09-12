"""Blok sıralama (sütun/satır bölme) ve Segment üretimi."""

from collections import Counter

from ...core.enums import ContentType
from ..types import Segment
from .constants import (
    HEADING_MAX_CHARS,
    HEADING_SIZE_RATIO,
    HEADING_STACK,
    MAX_CUT_DEPTH,
    MIN_COLUMN_GAP,
    MIN_COLUMN_GAP_RATIO,
    MIN_ROW_GAP,
    MIN_ROW_GAP_RATIO,
    PAGE_CONTEXT_CHARS,
)


def order_blocks(blocks: list[dict], width: float, height: float, depth: int = 0) -> list[dict]:
    """Okuma düzeninde sırala: büyük boşluklardan sütun/satır bölmeleriyle."""
    if len(blocks) <= 1 or depth >= MAX_CUT_DEPTH:
        return _sorted_by_pos(blocks)

    x_gap = _largest_gap(blocks, 0)
    y_gap = _largest_gap(blocks, 1)

    if x_gap and x_gap[0] >= max(MIN_COLUMN_GAP, width * MIN_COLUMN_GAP_RATIO):
        cut = x_gap[1]
        left = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 < cut]
        right = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) / 2 >= cut]
        if len(left) >= 2 and len(right) >= 2:
            return order_blocks(left, width, height, depth + 1) + order_blocks(
                right, width, height, depth + 1
            )

    if y_gap and y_gap[0] >= max(MIN_ROW_GAP, height * MIN_ROW_GAP_RATIO):
        cut = y_gap[1]
        upper = [b for b in blocks if (b["bbox"][1] + b["bbox"][3]) / 2 < cut]
        lower = [b for b in blocks if (b["bbox"][1] + b["bbox"][3]) / 2 >= cut]
        if upper and lower:
            return order_blocks(upper, width, height, depth + 1) + order_blocks(
                lower, width, height, depth + 1
            )

    return _sorted_by_pos(blocks)


def inject_anchors(ordered: list[dict], anchors: list[dict]) -> list[dict]:
    """Tablo/görsel gibi geniş blokları XY-cut sıralı metin akışına y-merkezlerine göre eker.

    Birleştirilmiş akışta anchor, y-merkezinin ardına düştüğü ilk metin bloğundan önce
    konumlanır; böylece tablo/görsel okuma düzenine uygun konuma oturur ve
    sütun kesimlerini (XY-cut) bozmaz.
    """
    if not anchors:
        return ordered
    flow = list(ordered)
    for a in sorted(anchors, key=lambda it: (it["bbox"][1] + it["bbox"][3]) / 2):
        ay = (a["bbox"][1] + a["bbox"][3]) / 2
        idx = 0
        while idx < len(flow) and ay > (flow[idx]["bbox"][1] + flow[idx]["bbox"][3]) / 2:
            idx += 1
        flow.insert(idx, a)
    return flow


def body_font_size(items: list[dict]) -> float:
    sizes = [it["size"] for it in items if it["kind"] == "text" and it["size"] >= 4]
    if not sizes:
        return 11.0
    counts = Counter(sizes)
    best = max(counts.values())
    return min(s for s, c in counts.items() if c == best)


def emit_segments(ordered: list[dict], page_number: int, body_size: float) -> list[Segment]:
    """Sıralı item listesini başlık/breadcrumb etiketiyle Segment'lere dönüştürür."""
    fallback_ctx = " ".join(it["text"] for it in ordered if it["kind"] == "text")[:PAGE_CONTEXT_CHARS]
    headings: list[tuple[str, float]] = []
    last_heading_size = 0.0

    def ctx() -> str:
        if headings:
            return " | ".join(h[0] for h in headings)
        return fallback_ctx

    segments: list[Segment] = []
    for order, it in enumerate(ordered):
        crumbs = [h[0] for h in headings]
        if it["kind"] != "text":
            text = it["text"]
            if it["kind"] == "table":
                label = it.get("caption") or (" | ".join(h[0] for h in headings)) or fallback_ctx
                if label:
                    text = f"[Tablo: {label}]\n{text}"
            segments.append(
                Segment(
                    content_type=it["ctype"],
                    text=text,
                    page_number=page_number,
                    bbox=[it["bbox"]],
                    order=order,
                    page_context=ctx(),
                    breadcrumbs=crumbs,
                    image_path=it.get("image_path", ""),
                    image_kind=it.get("image_kind", ""),
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
                breadcrumbs=crumbs,
            )
        )
    return segments


def _sorted_by_pos(blocks: list[dict]) -> list[dict]:
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