/**
 * Panel sabit enums — web-api tarafındaki (backend) değerlerle birebir uyumlu.
 * Değerler DB/API string'leri olduğundan as const nesne + türetilmiş tip kullanılır.
 */

export const DocumentStatus = {
  Uploading: "uploading",
  Pending: "pending",
  Embedding: "embedding",
  Embedded: "embedded",
  Failed: "failed",
  Cancelled: "cancelled",
} as const
export type DocumentStatus = (typeof DocumentStatus)[keyof typeof DocumentStatus]

export const EmbeddingStatus = {
  Pending: "pending",
  Running: "running",
  Completed: "completed",
  Failed: "failed",
  Cancelled: "cancelled",
} as const
export type EmbeddingStatus = (typeof EmbeddingStatus)[keyof typeof EmbeddingStatus]

export const SummaryStatus = {
  Pending: "pending",
  Done: "done",
  Failed: "failed",
} as const
export type SummaryStatus = (typeof SummaryStatus)[keyof typeof SummaryStatus]

export const ContentType = {
  Text: "text",
  Table: "table",
  OcrText: "ocr_text",
  Image: "image",
  Code: "code",
  Equation: "equation",
} as const
export type ContentType = (typeof ContentType)[keyof typeof ContentType]

export const ImageKind = {
  ImageCaption: "image_caption",
  Diagram: "diagram",
  FormData: "form_data",
  ScannedPage: "scanned_page",
} as const
export type ImageKind = (typeof ImageKind)[keyof typeof ImageKind]

export const UserType = {
  Admin: "admin",
  User: "user",
} as const
export type UserType = (typeof UserType)[keyof typeof UserType]