"""PyMuPDF blok sözlüğünden metin/kod/tablo "item"larını toplar."""

from ...core.enums import ContentType
from . import equations
from .tables import table_caption, table_to_markdown

_MONO_MARKERS = ("cour", "mono", "consol")


def _is_code_block(block: dict) -> bool:
    mono_lines = 0
    total = 0
    for line in block.get("lines", []):
        spans = [sp for sp in line.get("spans", []) if sp.get("text", "").strip()]
        if not spans:
            continue
        total += 1
        font = (spans[0].get("font") or "").lower()
        if any(marker in font for marker in _MONO_MARKERS):
            mono_lines += 1
    return total > 0 and mono_lines / total >= 0.6


def overlaps_table(bbox, table_list) -> bool:
    bx0, by0, bx1, by1 = bbox
    barea = max(bx1 - bx0, 0) * max(by1 - by0, 0)
    if barea <= 0:
        return False
    for t in table_list:
        tb = t.bbox
        ix0, iy0 = max(bx0, tb[0]), max(by0, tb[1])
        ix1, iy1 = min(bx1, tb[2]), min(by1, tb[3])
        if max(ix1 - ix0, 0) * max(iy1 - iy0, 0) / barea > 0.5:
            return True
    return False


def _text_item(
    block: dict,
    top: float,
    bottom: float,
    table_list,
    skip: set[str] | None = None,
    skip_top: float = 0.0,
    skip_bottom: float = float("inf"),
) -> dict | None:
    bx0, by0, bx1, by1 = block["bbox"]
    if by1 < top or by0 > bottom:
        return None
    if overlaps_table(block["bbox"], table_list):
        return None

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
        return None
    if skip and (by1 <= skip_top or by0 >= skip_bottom):
        norm = " ".join(text.lower().split())
        if norm in skip:
            return None
    if _is_code_block(block):
        return {
            "kind": "code",
            "bbox": (float(bx0), float(by0), float(bx1), float(by1)),
            "text": f"```\n{text}\n```",
            "ctype": ContentType.code.value,
        }
    return {
        "kind": "text",
        "bbox": (float(bx0), float(by0), float(bx1), float(by1)),
        "text": text,
        "size": max(sizes) if sizes else 0.0,
        "bold": bold,
    }


def collect_items(
    block_data: list[dict],
    table_list,
    top: float,
    bottom: float,
    skip: set[str] | None = None,
    skip_top: float = 0.0,
    skip_bottom: float = float("inf"),
    page_width: float = 0.0,
) -> list[dict]:
    """Sayfa bloğu sözlüğünden metin/kod/tablo/denklem item'larını sıralamasız toplar.

    `page_width > 0` ise blok denklem tespiti çalışır: denklem bloğu yerel LaTeX'e
    çevrilmeye çalışılır (`kind = "equation"`), başarısızsa görsel fallback işaretlenir
    (pdf.py'de `equations.vision_fixup`).

    `skip`: sayfalar arası tekrar eden başlık/altbilgi metin seti; y-bandındaki bloklar
    bunlardan biriyse elenir (frekans temelli header/footer budaması, rag_arch §A2).
    """
    items: list[dict] = []
    for block in block_data:
        if block.get("type") != 0:
            continue
        bx0, by0, bx1, by1 = block["bbox"]
        if by1 < top or by0 > bottom:
            continue
        if page_width > 0 and equations.is_block_equation(block, page_width):
            item = equations.equation_item(block)
            if item:
                items.append(item)
            continue
        item = _text_item(block, top, bottom, table_list, skip, skip_top, skip_bottom)
        if item:
            items.append(item)

    for t in table_list:
        md = table_to_markdown(t)
        if not md:
            continue
        tb = t.bbox
        items.append(
            {
                "kind": "table",
                "bbox": (tb[0], tb[1], tb[2], tb[3]),
                "text": md,
                "ctype": ContentType.table.value,
                "caption": table_caption(block_data, tb),
            }
        )
    return items