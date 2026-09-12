export type DocumentStatusValue =
  | "uploading"
  | "pending"
  | "embedding"
  | "embedded"
  | "failed"
  | "cancelled"

export interface DocumentItem {
  id: string
  filename: string
  file_type?: string
  size: number
  status: DocumentStatusValue | string
  chunk_count?: number
  error?: string | null
  stats?: object | null
  summary?: string | null
  summary_status?: string | null
  summary_error?: string | null
  starter_questions?: string[] | null
  created_at?: string
  updated_at?: string
}