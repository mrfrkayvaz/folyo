"""Tesseract OCR — tur+eng; çıktı istatistikleriyle yoğunluk testi (rag_arch §2C).

Yoğunluk testi: resmin "çoğu yazıdan mı oluştuğunu" dört metrikle ölçer.
Testi geçemeyen görseller Vision LLM'e düşer.
"""

import io

import pytesseract
from PIL import Image

from ..core.config import get_settings


def ocr_image(image_bytes: bytes) -> dict:
    """Tesseract ile görseli okur; metin + istatistik döndürür."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Görsel açılamadı: {exc}") from exc

    data = pytesseract.image_to_data(
        img, lang=get_settings().ocr_langs, output_type=pytesseract.Output.DICT
    )

    n = len(data.get("text", []))
    words: list[str] = []
    confs: list[float] = []
    area = 0.0
    img_area = max(img.size[0] * img.size[1], 1)

    for i in range(n):
        w = (data["text"][i] or "").strip()
        try:
            conf = float(data["conf"][i])
        except (KeyError, ValueError, TypeError):
            conf = 0.0
        if not w:
            continue
        words.append(w)
        if conf >= 0:
            confs.append(conf)
        try:
            x, y, ww, hh = (
                int(data["left"][i]),
                int(data["top"][i]),
                int(data["width"][i]),
                int(data["height"][i]),
            )
            area += max(ww, 0) * max(hh, 0)
        except (KeyError, ValueError, TypeError):
            pass

    text = " ".join(words)
    return {
        "text": text,
        "mean_conf": (sum(confs) / len(confs)) if confs else 0.0,
        "alnum_ratio": (sum(1 for ch in text if ch.isalnum()) / len(text)) if text else 0.0,
        "word_count": len(words),
        "text_coverage": min(area / img_area, 1.0),
    }


def is_mostly_text(stats: dict, settings) -> bool:
    """Dört eşik birlikte sağlanırsa OCR metni kabul edilir."""
    return (
        stats["mean_conf"] >= settings.ocr_min_confidence
        and stats["alnum_ratio"] >= settings.ocr_min_alnum_ratio
        and stats["word_count"] >= settings.ocr_min_words
        and stats["text_coverage"] >= settings.ocr_min_text_coverage
    )