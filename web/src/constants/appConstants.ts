import type { ConfidenceLevel } from "../types/chatTypes"

export const THEME_KEY = "folyo_theme"
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
export const DEFAULT_CHAT_TITLE = "Yeni sohbet"
export const STATUS_POLL_INTERVAL_MS = 2000

export const ALLOWED_EXTENSIONS: RegExp = /^([^.]+\.)?(pdf|txt|md|png|jpg|jpeg|webp|bmp|tif|tiff)$/i
export const ACCEPTED_FILE_ATTR = ".pdf,.txt,.md,.jpg,.jpeg,.png,.webp"

export const UNSUPPORTED_FILES_MSG = "Yalnızca PDF, JPG, PNG, TXT veya MD dosyaları yüklenebilir."
export const PARTIAL_UNSUPPORTED_MSG =
  "Bazı dosyalar desteklenmiyor ve atlandı. (Yalnızca PDF · JPG · PNG · TXT · MD)"

export const SSE_EVENTS = {
  DELTA: "delta",
  META: "meta",
  ERROR: "error",
  DONE: "done",
} as const

export type SseEventName = (typeof SSE_EVENTS)[keyof typeof SSE_EVENTS]

export const CONTENT_TYPE_LABELS: Record<string, string> = {
  text: "metin",
  table: "tablo",
  ocr_text: "OCR metni",
  image: "görsel",
  code: "kod",
}

export const CONFIDENCE_LEVELS: Record<ConfidenceLevel, { label: string; cls: string }> = {
  yüksek: { label: "Yüksek güven", cls: "badge-success" },
  orta: { label: "Orta güven", cls: "badge-warning" },
  dolaylı: { label: "Dolaylı güven", cls: "badge-info" },
  yetersiz: { label: "Yetersiz bilgi", cls: "badge-error" },
}