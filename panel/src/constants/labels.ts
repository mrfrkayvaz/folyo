export const CONTENT_TYPE_LABELS: Record<string, string> = {
  text: "metin",
  table: "tablo",
  ocr_text: "OCR metni",
  image: "görsel",
  code: "kod",
}

export const IMAGE_KIND_LABELS: Record<string, string> = {
  image_caption: "grafik",
  diagram: "diyagram",
  form_data: "form",
  scanned_page: "taranmış sayfa",
}

export const DOC_STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  uploading: { label: "yükleniyor", cls: "badge-info" },
  pending: { label: "sırada", cls: "badge-warning" },
  embedding: { label: "işleniyor", cls: "badge-info" },
  embedded: { label: "hazır", cls: "badge-success" },
  failed: { label: "hata", cls: "badge-error" },
  cancelled: { label: "iptal", cls: "badge-neutral" },
}

export const SUMMARY_STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  pending: { label: "özet bekliyor", cls: "badge-warning" },
  done: { label: "özet hazır", cls: "badge-success" },
  failed: { label: "özet hata", cls: "badge-error" },
}