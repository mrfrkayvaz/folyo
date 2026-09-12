import type { DocumentStatusValue } from "./documentTypes"

export type AttachmentPhase = DocumentStatusValue | "queued"

export interface Attachment {
  key: string
  file?: File
  filename?: string
  size?: number
  docId?: string | null
  phase: AttachmentPhase
  progress?: number
  error?: string
  stats?: object | null
  summary?: string
  summaryStatus?: string
  summaryError?: string
  starterQuestions?: string[]
  /** Önizleme modalında hedef (atıf rozetinden gelir). */
  targetPage?: number | null
  targetChunk?: number | null
}