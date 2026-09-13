import { describe, expect, it } from "vitest"
import {
  ACCEPTED_FILE_ATTR,
  ALLOWED_EXTENSIONS,
  CONFIDENCE_LEVELS,
  CONTENT_TYPE_LABELS,
  DEFAULT_CHAT_TITLE,
  MAX_FILE_SIZE_BYTES,
  SSE_EVENTS,
  STATUS_POLL_INTERVAL_MS,
  THEME_KEY,
  UNSUPPORTED_FILES_MSG,
} from "./index"

describe("boyut ve süre sabitleri", () => {
  it("MAX_FILE_SIZE_BYTES 25 MB", () => {
    expect(MAX_FILE_SIZE_BYTES).toBe(25 * 1024 * 1024)
  })

  it("tema anahtarı ve başlık", () => {
    expect(THEME_KEY).toBe("folyo_theme")
    expect(DEFAULT_CHAT_TITLE).toBe("Yeni sohbet")
  })

  it("polling aralığı 2 sn", () => {
    expect(STATUS_POLL_INTERVAL_MS).toBe(2000)
  })
})

describe("ALLOWED_EXTENSIONS", () => {
  it("desteklenen uzantıları kabul eder (büyük/küçük harf duyarsız)", () => {
    for (const name of ["rapor.pdf", "rapor.PDF", "foto.jpg", "foto.JPEG", "webp.webp",
      "tarama.tif", "tarama.tiff", "not.md", "notlar.txt", "ad boşluklu.png"]) {
      expect(ALLOWED_EXTENSIONS.test(name), name).toBe(true)
    }
  })

  it("desteklenmeyenleri reddeder", () => {
    for (const name of ["", "rapor.exe", "belge.pdfx", "foto.pngz", "resim.png.bak", "noext"]) {
      expect(ALLOWED_EXTENSIONS.test(name), name).toBe(false)
    }
  })

  it("ACCEPTED_FILE_ATTR backend allowlist ile uyumlu", () => {
    expect(ACCEPTED_FILE_ATTR).toContain(".pdf")
    expect(ACCEPTED_FILE_ATTR).toContain(".png")
    expect(ACCEPTED_FILE_ATTR).toContain(".txt")
  })
})

describe("etiket eşlemeleri", () => {
  it("içerik türü etiketleri", () => {
    expect(CONTENT_TYPE_LABELS.text).toBe("metin")
    expect(CONTENT_TYPE_LABELS.table).toBe("tablo")
    expect(CONTENT_TYPE_LABELS.ocr_text).toBe("OCR metni")
    expect(CONTENT_TYPE_LABELS.image).toBe("görsel")
    expect(CONTENT_TYPE_LABELS.code).toBe("kod")
  })

  it("güven seviyeleri rozet sınıfları", () => {
    expect(CONFIDENCE_LEVELS.yüksek.cls).toBe("badge-success")
    expect(CONFIDENCE_LEVELS.orta.cls).toBe("badge-warning")
    expect(CONFIDENCE_LEVELS.dolaylı.cls).toBe("badge-info")
    expect(CONFIDENCE_LEVELS.yetersiz.cls).toBe("badge-error")
  })

  it("kullanıcı dostu hata mesajları tanımlı", () => {
    expect(UNSUPPORTED_FILES_MSG).toContain("PDF")
  })
})

describe("SSE_EVENTS", () => {
  it("SSE olay adları", () => {
    expect(SSE_EVENTS.DELTA).toBe("delta")
    expect(SSE_EVENTS.META).toBe("meta")
    expect(SSE_EVENTS.ERROR).toBe("error")
    expect(SSE_EVENTS.DONE).toBe("done")
  })
})