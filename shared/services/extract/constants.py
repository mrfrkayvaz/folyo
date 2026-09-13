"""Harici sabitler: desteklenen uzantılar ve sayfa düzeni eşikleri."""

PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}
TEXT_EXTS = {".txt", ".md"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Upload allowlist'i + hata mesajları için tek kaynak.
SUPPORTED_EXTS = PDF_EXTS | DOCX_EXTS | TEXT_EXTS | IMAGE_EXTS

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

PIXMAP_ZOOM = 2.0