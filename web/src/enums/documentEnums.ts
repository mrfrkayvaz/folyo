export const DocumentStatus = {
  UPLOADING: "uploading",
  PENDING: "pending",
  EMBEDDING: "embedding",
  EMBEDDED: "embedded",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const

export type DocumentStatusKey = (typeof DocumentStatus)[keyof typeof DocumentStatus]