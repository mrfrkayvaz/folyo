"""Blok denklem işleme: tespit → yerel LaTeX (pylatexenc) → Vision fallback.

Folyo felsefesi: aşamalı ve maliyet/hız optimize.
- Inline denklemler PyMuPDF doğal akışında (Unicode) `text` olarak kalır — işlenmez.
- Blok denklemler `is_block_equation` ile tespit edilir:
    1. Yerel hafif araç (`pylatexenc`, $0, ~1 ms) Unicode'u LaTeX'e çevirir.
    2. Yerel çözemezse VEYA Office glifleri (PUA) içeriyorsa → bbox kırpılır,
       Vision LLM'e gönderilir (`vision.describe_image`), saf LaTeX alınır.
- Vision tanımlı değilse raw Unicode korunur (kırılma yok).
"""

import asyncio
import re

import pymupdf

from ...core.config import get_settings
from shared.core.enums import ContentType
from shared.core.logging import get_logger
from .. import vision

LOG = get_logger("extract.equations")

# Matematik font adları (alt dize eşleşmesi — subsetli font adları da yakalanır).
MATH_FONTS = (
    "cmsy", "cmmi", "cmr", "cambria math", "stix", "latinmodernmath",
    "asana math", "mathjax", "mathtime",
)

# Blok denklem tespitinde sayılan semboller.
MATH_SYMBOLS = set("=+-*/^_∑∫√αβγδθλε≤≥±≠≈∂∇λπ∞×⋅÷μφωηρ")


def has_pua(block: dict) -> bool:
    """Office (OMML) kökenli denklem glifleri Özel Kullanım Alanında (U+E000–U+F8FF)
    çizilir; PyMuPDF bunları metin olarak çıkarır ama yerel Unicode→LaTeX çevirimi çözemez.
    Bu bloklar doğrudan Vision fallback'i gerektirir."""
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            for ch in span.get("text", "") or "":
                if 0xE000 <= ord(ch) <= 0xF8FF:
                    return True
    return False


def _block_stats(block: dict) -> tuple[str, int, int, bool]:
    """(metin, anlamlı karakter sayısı, sembol sayısı, matematik fontu var mı)."""
    text_parts: list[str] = []
    total = 0
    math_count = 0
    math_font = False
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            t = span.get("text") or ""
            font = (span.get("font") or "").lower()
            if any(mf in font for mf in MATH_FONTS):
                math_font = True
            text_parts.append(t)
            for ch in t:
                if ch.isspace():
                    continue
                total += 1
                if ch in MATH_SYMBOLS:
                    math_count += 1
    return "".join(text_parts), total, math_count, math_font


def is_block_equation(block: dict, page_width: float, settings=None) -> bool:
    """Blok bağımsız bir denklem mi? Font + sembol yoğunluğu + geometri (ortalama/denklem no)."""
    settings = settings or get_settings()
    lines = block.get("lines") or []
    if not lines or len(lines) > settings.equation_max_lines:
        return False
    text, total, math_count, math_font = _block_stats(block)
    if total == 0:
        return False
    ratio = math_count / total
    # Kısa denklemlerde (E = mc², F = ma) sembol oranı doğal olarak düşük olabilir:
    # ≤12 karakter ve en az 1 matematik sembolü → yine de aday.
    short_eq = total <= 12 and math_count >= 1
    is_math_heavy = math_font or (ratio >= settings.equation_min_symbol_ratio and total < 250) or short_eq
    if not is_math_heavy:
        return False

    bbox = block.get("bbox") or (0.0, 0.0, 0.0, 0.0)
    m = settings.equation_center_margin
    is_centered = bbox[0] >= page_width * m and bbox[2] <= page_width * (1 - m)
    has_eq_number = bool(re.search(r"\(\s*\d+(?:\.\d+)?\s*\)\s*$", text.strip()))
    return is_centered or has_eq_number


def try_local_latex(block: dict, settings=None) -> tuple[bool, str]:
    """Aşama 1 (yerel): Unicode metni LaTeX'e çevirir; yapısal olarak kayda değer çıktı bekler."""
    settings = settings or get_settings()
    text, total, math_count, _ = _block_stats(block)
    if not text.strip() or total == 0:
        return False, ""
    # Sondaki denklem numarasını (1), (2.1) LaTeX'e sokma — vision prompt'uyla tutarlı.
    text = re.sub(r"\(\s*\d+(?:\.\d+)?\s*\)\s*$", "", text.strip())
    if not text.strip():
        return False, ""
    lines = block.get("lines") or []
    # Alt alta glifler (fraksiyon/matris bozulması): her satır tek span → yerel çözemez.
    if len(lines) > 2 and any(len(line.get("spans") or []) == 1 for line in lines):
        return False, ""
    if has_pua(block):
        return False, ""
    try:
        from pylatexenc.latexencode import unicode_to_latex
        # pylatexenc Yunanca/özel karakterleri `\ensuremath{...}` ile sarar; KaTeX dostu
        # doğrudan komutlara (`\alpha`) sadeleştir.
        candidate = unicode_to_latex(text).strip()
        candidate = re.sub(r"\\ensuremath\{([^{}]*)\}\s*", r"\1", candidate)
    except Exception:
        return False, ""
    if not candidate or has_pua({"lines": [{"spans": [{"text": candidate}]}]}):
        return False, ""
    has_construct = any(
        tok in candidate for tok in ("\\", "=", "+", "-", "^", "_", "*", "/", "≤", "≥", "≠")
    )
    has_operand = any(ch.isalnum() for ch in candidate)
    if has_construct and has_operand and len(candidate) >= 2:
        return True, f"$${candidate}$$"
    return False, ""


def equation_item(block: dict, settings=None) -> dict | None:
    """Denklem bloğundan item üretir; yerel çevrim başarısızsa görsel fallback işaretler."""
    settings = settings or get_settings()
    text, _, _, _ = _block_stats(block)
    if not text.strip():
        return None
    local_ok, latex = try_local_latex(block, settings)
    item = {
        "kind": "equation",
        "bbox": [float(v) for v in (block.get("bbox") or [0, 0, 0, 0])],
        "text": latex if local_ok else text,
        "ctype": ContentType.equation.value,
        "image_path": "",
        "image_kind": "",
        "size": 0.0,
        "bold": False,
    }
    if not local_ok:
        item["needs_vision"] = True
        item["block_ref"] = block
    return item


async def _equation_image(page, bbox, settings) -> bytes | None:
    """Denklemi sayfadan kırpar (nefes payıyla, sayfa sınırına kırpılmış); boşsa `None`."""
    rect = pymupdf.Rect(bbox) + (-settings.equation_vision_padding,) * 4
    rect &= page.rect
    if rect.is_empty or rect.width <= 0 or rect.height <= 0:
        return None
    pix = page.get_pixmap(clip=rect, dpi=settings.equation_vision_dpi)
    return pix.tobytes("png")


async def extract_equation_via_vision(page, bbox, settings) -> str:
    """Aşama 2 (Vision): bbox kırpımını Vision LLM'e gönderir, saf `$$...$$` LaTeX döndürür."""
    image = await _equation_image(page, bbox, settings)
    if image is None:
        LOG.warning("[eq] kırpım BOŞ (sayfa sınırı dışı?): bbox=%s", [round(v, 1) for v in bbox])
        return ""
    LOG.info(
        "[eq] Vision denklem: bbox=%s kırpım=%d B (padding=%d dpi=%d)",
        [round(v, 1) for v in bbox],
        len(image),
        settings.equation_vision_padding,
        settings.equation_vision_dpi,
    )
    try:
        latex = (await vision.describe_image(image, "equation")).strip()
    except Exception as exc:
        LOG.error("[eq] Vision denklem HATASI: %s", exc, exc_info=True)
        return ""
    if not latex or latex == r"\text{okunamadı}":
        LOG.warning("[eq] Vision okunamadı döndürdü: %r — raw Unicode kalıyor", (latex or "")[:60])
        return ""
    LOG.info("[eq] Vision LaTeX alındı: %d karakter", len(latex))
    if latex.startswith("$$") and latex.endswith("$$"):
        latex = latex[2:-2].strip()
    return f"$${latex}$$"


async def vision_fixup(page, items, settings) -> None:
    """`needs_vision` işaretli denklem item'larını Vision ile çözer; vision yoksa raw kalır.

    Çağrılar `asyncio.gather` ile paralel akar (Vision tarafı `vision._VISION_SEM`
    ile sınırlıdır); sonuçlar item sırasına göre geri atanır.
    """
    todo = [it for it in items if it.get("needs_vision")]
    if not todo:
        return
    if settings.vision_ready:
        latexes = await asyncio.gather(
            *(extract_equation_via_vision(page, it["bbox"], settings) for it in todo)
        )
        resolved = sum(1 for l in latexes if l)
        LOG.info(
            "[eq] vision_fixup: %d denklem adayı, %d tanesi Vision ile çözüldü, %d raw kaldı",
            len(todo),
            resolved,
            len(todo) - resolved,
        )
        for it, latex in zip(todo, latexes):
            if latex:
                it["text"] = latex
    else:
        LOG.info(
            "[eq] vision_ready=False — %d denklem Vision'sız raw Unicode olarak kaldı", len(todo)
        )
    for it in todo:
        it.pop("block_ref", None)
        it.pop("needs_vision", None)