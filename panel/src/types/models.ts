export interface PanelWorkspace {
  id: string
  name: string
  created_at: string
  last_message_at?: string | null
  doc_count?: number
  message_count?: number
  summary?: string | null
  summary_docs?: string[] | null
}

export interface JobInfo {
  status?: string
  dim?: number
  chunks?: number
  progress?: number
  error?: string | null
}

export interface PanelDocument {
  id: string
  filename: string
  file_type?: string
  size?: number
  status: string
  chunk_count?: number
  error?: string | null
  summary?: string | null
  summary_status?: string | null
  summary_error?: string | null
  questions?: string[]
  created_at?: string
  updated_at?: string
  process?: { job?: JobInfo | null }
}

export interface ChunkItem {
  chunk_index: number
  page_number: number
  content_type: string
  image_kind?: string
  image_path?: string
  section_title?: string
  text: string
}

export interface DocumentDetailResponse {
  document: PanelDocument
  chunks: ChunkItem[]
}

export interface WorkspaceDetailResponse {
  workspace: PanelWorkspace
  documents: PanelDocument[]
}