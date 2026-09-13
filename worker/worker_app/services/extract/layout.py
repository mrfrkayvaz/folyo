"""Blok sıralama (sütun/satır bölme) ve Segment üretimi."""

import re
from collections import Counter

from shared.core.enums import ContentType
from shared.services.types import Segment
from shared.services.extract.constants import (
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


def _clean_heading(text: str) -> str:
    """Başlık/gezinme ön ekini temizler: ok/glif gürültüsü, kontrol karakterleri, tekrar boşluk."""
    cleaned = re.sub(r"[➨➔→\u0000-\u001f]", " ", text)
    return " ".join(cleaned.split())


def _same_heading(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


# Liste/madde öğesi başlangıç işaretleri: ok/glif öğeleri, madde işaretleri, çizgiler, numaralar.
# Boş satırın başladığı bu öğeler bir başlık değil, listenin DEVAMI olan içerik satırlarıdır;
# başlık algılamasından dışlanmaları gerekir (yoksa her madde ayrı breadcrumb/chunk olur).
_LIST_MARK_RE = re.compile(
    r"^\s*(?:(?:[➨➔→•·∙◦○●◉■▪‣➢])|(?:[-–—]\s)|(?:\*\s)|(?:\+\s)"
    r"|(?:\d{1,3}[.)]\s*)|(?:\(\d{1,3}\)\s*))"
)


def _is_list_item(text: str) -> bool:
    """Satır bir liste/madde öğesiyle mi başlıyor? (➨ • - 1. vb.)"""
    return bool(_LIST_MARK_RE.match(text))


def emit_segments(ordered: list[dict], page_number: int, body_size: float) -> list[Segment]:
    """Sıralı item listesini başlık/breadcrumb etiketiyle Segment'lere dönüştürür.

    Metin item'ları **satır satır** işlenir: blok içinde başlık benzeri bir satır
    (font kuralı VEYA kısa iki-nokta ile biten satır) breadcrumb'ı günceller ve orada
    konu sınırı çizilir — böylece farklı başlıkların metni aynı chunk'a karışmaz
    (embed kalitesi ve dense sıralama için kritik).
    """
    fallback_ctx = " ".join(it["text"] for it in ordered if it["kind"] == "text")[:PAGE_CONTEXT_CHARS]
    headings: list[tuple[str, float]] = []
    last_heading_size = 0.0
    threshold = max(body_size * HEADING_SIZE_RATIO, body_size + 1.0)

    def ctx() -> str:
        if headings:
            return " | ".join(h[0] for h in headings)
        return fallback_ctx

    def crumbs() -> list[str]:
        return [h[0] for h in headings]

    def push_heading(text: str, size: float) -> None:
        nonlocal last_heading_size
        clean = _clean_heading(text)
        if not clean:
            return
        prev = headings[-1][0] if headings else ""
        if headings and size >= last_heading_size * 0.85:
            headings[-1] = (clean, size)  # aynı büyüklük ailesi → konumu güncelle
        elif not _same_heading(clean, prev):
            headings.append((clean, size))
            if len(headings) > HEADING_STACK:
                headings.pop(0)
        elif headings:
            headings[-1] = (prev, size)  # ardışık tekrar → yığma
        last_heading_size = size

    def is_heading_line(text: str, size: float, bold: bool) -> str | None:
        """Başlık satırıysa breadcrumb'a girecek temiz metni döndürür, değilse None.

        Kurallar: font kuralı; iki-nokta ile biten kısa satır (`Epirojenez:`);
        ya da caption kalıbı `Başlık: gövde…` (kısa ön ek + satır başı büyük harf).
        """
        clean = _clean_heading(text)
        if not clean or len(clean) > HEADING_MAX_CHARS:
            return None
        # Madde/liste öğeleri başlık DEĞİLDİR: aynı tema altında tek chunk'ta birleşmeli.
        # (Kaynak belgelerde liste öğeleri gövdeden büyük/kalın olabiliyor — font kuralı
        #  bunları başlık sanıp her maddeyi ayrı konuya/chunk'a ayırıyor.)
        if _is_list_item(text):
            return None
        if size >= threshold or (bold and size > body_size):
            return clean
        if len(clean) <= 70 and clean.endswith(":"):
            return clean
        m = re.match(r"^([^:]{3,60}):\s", text)
        if m and text[0].isupper() and len(clean) <= 240:
            return _clean_heading(m.group(1)) + ":"
        return None

    segments: list[Segment] = []
    order = 0
    for it in ordered:
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
                    breadcrumbs=crumbs(),
                    image_path=it.get("image_path", ""),
                    image_kind=it.get("image_kind", ""),
                )
            )
            order += 1
            continue

        lines = it.get("lines") or [{"text": it["text"], "size": it["size"], "bold": it["bold"]}]
        buf: list[str] = []

        def flush_buf():
            nonlocal order
            text = "\n".join(buf).strip()
            buf.clear()
            if not text:
                return
            segments.append(
                Segment(
                    content_type=ContentType.text.value,
                    text=text,
                    page_number=page_number,
                    bbox=[it["bbox"]],
                    order=order,
                    page_context=ctx(),
                    breadcrumbs=crumbs(),
                )
            )
            order += 1

        for ln in lines:
            t = (ln.get("text") or "").strip()
            if not t:
                continue
            line_size = float(ln.get("size") or 0.0)
            heading = is_heading_line(t, line_size, bool(ln.get("bold")))
            if heading:
                flush_buf()
                push_heading(heading, line_size)
            buf.append(t)
        flush_buf()
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