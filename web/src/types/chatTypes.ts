export interface CitationSource {
  label: string
  meta?: string
}

export type ChatRoleValue = "user" | "assistant"

export type ConfidenceLevel = "yüksek" | "orta" | "dolaylı" | "yetersiz"

export interface SignalMeta {
  dense: number
  dense_min: number
  bm25: number
  bm25_min: number
}

export interface ChunkScore {
  id: string
  dense: number
  bm25: number
}

export interface ChatCitations {
  sources: CitationSource[]
  chunk_ids: string[]
  chunk_scores?: ChunkScore[]
  confidence?: number | null
  confidence_level?: ConfidenceLevel | null
  rejected?: boolean
  signals?: SignalMeta | null
}

export interface ApiMessage {
  id: string
  role: ChatRoleValue
  content: string
  created_at: string
  citations: ChatCitations | CitationSource[] | null
}

/** UI tarafında kullanılan sohbet mesajı (stream + kayıt birleşimi). */
export interface ChatMessageItem {
  id: string
  role: ChatRoleValue
  text: string
  createdAt: string
  streaming?: boolean
  /** Kullanıcı mesajına nesne eklentisi (opsiyonel). */
  file?: File
  sources?: CitationSource[]
  chunkIds?: string[]
  confidence?: number | null
  confidenceLevel?: ConfidenceLevel | null
  rejected?: boolean
  signals?: SignalMeta | null
  chunkScores?: ChunkScore[]
}

export type QaEventName = "delta" | "meta" | "error" | "done"

export interface CitationClickTarget {
  filename: string
  pageNumber: number | null
  chunkIndex: number
}

export interface QaMetaPayload {
  sources?: CitationSource[]
  chunk_ids?: string[]
  confidence?: number | null
  confidence_level?: ConfidenceLevel | null
  rejected?: boolean
  signals?: SignalMeta | null
}

export interface QaEventMap {
  delta: { text: string }
  meta: QaMetaPayload
  error: { message: string }
  done: QaMetaPayload
}

export type QaEventPayload = {
  [K in QaEventName]: QaEventMap[K]
}[QaEventName]