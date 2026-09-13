/** Panel geneli sabitler — etiket/rozet eşlemeleri (enum'larla tipli). */
import { ContentType, DocumentStatus, ImageKind, SummaryStatus } from "@/constants/enums"

export const CONTENT_TYPE_LABELS: Partial<Record<ContentType, string>> = {
  [ContentType.Text]: "metin",
  [ContentType.Table]: "tablo",
  [ContentType.OcrText]: "OCR metni",
  [ContentType.Image]: "görsel",
  [ContentType.Code]: "kod",
}

/** API'den gelebilecek bilinmeyen değerler için güvenli etiket (bilinmeyen → raw). */
export function contentTypeLabel(v: string): string {
  return CONTENT_TYPE_LABELS[v as ContentType] ?? v
}

export const IMAGE_KIND_LABELS: Partial<Record<ImageKind, string>> = {
  [ImageKind.ImageCaption]: "grafik",
  [ImageKind.Diagram]: "diyagram",
  [ImageKind.FormData]: "form",
  [ImageKind.ScannedPage]: "taranmış sayfa",
}

export function imageKindLabel(v: string): string {
  return IMAGE_KIND_LABELS[v as ImageKind] ?? v
}

export const DOC_STATUS_LABELS: Record<DocumentStatus, { label: string; cls: string }> = {
  [DocumentStatus.Uploading]: { label: "yükleniyor", cls: "badge-info" },
  [DocumentStatus.Pending]: { label: "sırada", cls: "badge-warning" },
  [DocumentStatus.Embedding]: { label: "işleniyor", cls: "badge-info" },
  [DocumentStatus.Embedded]: { label: "hazır", cls: "badge-success" },
  [DocumentStatus.Failed]: { label: "hata", cls: "badge-error" },
  [DocumentStatus.Cancelled]: { label: "iptal", cls: "badge-neutral" },
}

export const SUMMARY_STATUS_LABELS: Record<SummaryStatus, { label: string; cls: string }> = {
  [SummaryStatus.Pending]: { label: "özet bekliyor", cls: "badge-warning" },
  [SummaryStatus.Done]: { label: "özet hazır", cls: "badge-success" },
  [SummaryStatus.Failed]: { label: "özet hata", cls: "badge-error" },
}