import { DocumentStatus, type DocumentStatusKey } from "../enums/index"
import type { ChatMessageItem, CitationSource, ConfidenceLevel } from "../types/chatTypes"
import type { ApiMessage, ChatCitations } from "../types/chatTypes"

let idCounter = 0
export const nid = () => `m${++idCounter}`

let attachKey = 0
export const aid = () => `a${++attachKey}`

export function terminalPhase(p: string): boolean {
  return p === DocumentStatus.EMBEDDED || p === DocumentStatus.FAILED || p === DocumentStatus.CANCELLED
}

export function mapDocPhase(status: string): DocumentStatusKey {
  if (status === DocumentStatus.UPLOADING) return DocumentStatus.UPLOADING
  if (status === DocumentStatus.PENDING || status === DocumentStatus.EMBEDDING) return DocumentStatus.EMBEDDING
  if (status === DocumentStatus.EMBEDDED) return DocumentStatus.EMBEDDED
  if (status === DocumentStatus.FAILED) return DocumentStatus.FAILED
  return DocumentStatus.CANCELLED
}

function citationsOf(m: ApiMessage): ChatCitations | null {
  if (Array.isArray(m.citations)) return { sources: m.citations, chunk_ids: [] }
  return m.citations ?? null
}

export function mapApiMessage(m: ApiMessage): ChatMessageItem {
  const cit = citationsOf(m)
  const sources: CitationSource[] = cit?.sources ?? []
  return {
    id: m.id,
    role: m.role,
    text: m.content,
    createdAt: m.created_at,
    sources: sources.length ? sources : undefined,
    chunkIds: cit?.chunk_ids?.length ? cit.chunk_ids : undefined,
    confidence: cit?.confidence ?? undefined,
    confidenceLevel: (cit?.confidence_level as ConfidenceLevel | undefined) ?? undefined,
    rejected: cit?.rejected ?? undefined,
    signals: cit?.signals ?? undefined,
    chunkScores: cit?.chunk_scores ?? undefined,
  }
}

export type { DocumentStatusKey }