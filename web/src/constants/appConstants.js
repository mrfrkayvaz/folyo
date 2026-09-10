export const THEME_KEY = "folyo_theme"
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
export const DEFAULT_CHAT_TITLE = "Yeni sohbet"
export const STATUS_POLL_INTERVAL_MS = 2000

export const SSE_EVENTS = Object.freeze({
  DELTA: "delta",
  META: "meta",
  ERROR: "error",
  DONE: "done",
})

export const CONTENT_TYPE_LABELS = Object.freeze({
  text: "metin",
  table: "tablo",
  image_caption: "grafik",
  diagram: "diyagram",
  form_data: "form",
  ocr_text: "OCR metni",
  scanned_page: "taranmış sayfa",
})

export const CONFIDENCE_LEVELS = Object.freeze({
  yüksek: { label: "Yüksek güven", cls: "badge-success" },
  orta: { label: "Orta güven", cls: "badge-warning" },
  dolaylı: { label: "Dolaylı güven", cls: "badge-info" },
  yetersiz: { label: "Yetersiz bilgi", cls: "badge-error" },
})
