import { describe, expect, it } from "vitest"
import {
  CONTENT_TYPE_LABELS,
  contentTypeLabel,
  DOC_STATUS_LABELS,
  IMAGE_KIND_LABELS,
  imageKindLabel,
  SUMMARY_STATUS_LABELS,
} from "./labels"
import { ContentType, DocumentStatus, ImageKind, SummaryStatus } from "./enums"

describe("contentTypeLabel", () => {
  it("bilinen değerler Türkçe etikete çevrilir", () => {
    expect(contentTypeLabel(ContentType.Text)).toBe("metin")
    expect(contentTypeLabel(ContentType.Table)).toBe("tablo")
    expect(contentTypeLabel(ContentType.OcrText)).toBe("OCR metni")
    expect(contentTypeLabel(ContentType.Image)).toBe("görsel")
    expect(contentTypeLabel(ContentType.Code)).toBe("kod")
  })

  it("bilinmeyen değer olduğu gibi döner (güvenli fallback)", () => {
    expect(contentTypeLabel("bilinmeyen_tip")).toBe("bilinmeyen_tip")
    expect(contentTypeLabel("")).toBe("")
  })

  it("CONTENT_TYPE_LABELS equation içermez (görünüm etiketi yok)", () => {
    expect(CONTENT_TYPE_LABELS[ContentType.Equation]).toBeUndefined()
  })
})

describe("imageKindLabel", () => {
  it("bilinen türler", () => {
    expect(imageKindLabel(ImageKind.ImageCaption)).toBe("grafik")
    expect(imageKindLabel(ImageKind.Diagram)).toBe("diyagram")
    expect(imageKindLabel(ImageKind.FormData)).toBe("form")
    expect(imageKindLabel(ImageKind.ScannedPage)).toBe("taranmış sayfa")
  })

  it("bilinmeyen raw döner", () => {
    expect(imageKindLabel("penguen")).toBe("penguen")
  })

  it("IMAGE_KIND_LABELS tam eşleşme haritası", () => {
    expect(Object.keys(IMAGE_KIND_LABELS)).toHaveLength(4)
  })
})

describe("DOC_STATUS_LABELS", () => {
  it("her durum için label + rozet sınıfı", () => {
    expect(DOC_STATUS_LABELS[DocumentStatus.Uploading]).toEqual({ label: "yükleniyor", cls: "badge-info" })
    expect(DOC_STATUS_LABELS[DocumentStatus.Pending]).toEqual({ label: "sırada", cls: "badge-warning" })
    expect(DOC_STATUS_LABELS[DocumentStatus.Embedding]).toEqual({ label: "işleniyor", cls: "badge-info" })
    expect(DOC_STATUS_LABELS[DocumentStatus.Embedded]).toEqual({ label: "hazır", cls: "badge-success" })
    expect(DOC_STATUS_LABELS[DocumentStatus.Failed]).toEqual({ label: "hata", cls: "badge-error" })
    expect(DOC_STATUS_LABELS[DocumentStatus.Cancelled]).toEqual({ label: "iptal", cls: "badge-neutral" })
  })
})

describe("SUMMARY_STATUS_LABELS", () => {
  it("üç durum da tanımlı", () => {
    expect(SUMMARY_STATUS_LABELS[SummaryStatus.Pending].label).toBe("özet bekliyor")
    expect(SUMMARY_STATUS_LABELS[SummaryStatus.Done].label).toBe("özet hazır")
    expect(SUMMARY_STATUS_LABELS[SummaryStatus.Failed].label).toBe("özet hata")
  })
})