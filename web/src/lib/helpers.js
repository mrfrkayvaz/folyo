import { DocumentStatus } from "../enums/index.js"

let idCounter = 0
export const nid = () => `m${++idCounter}`

let attachKey = 0
export const aid = () => `a${++attachKey}`

export function terminalPhase(p) {
  return p === DocumentStatus.EMBEDDED || p === DocumentStatus.FAILED || p === DocumentStatus.CANCELLED
}

export function mapDocPhase(status) {
  if (status === DocumentStatus.UPLOADING) return DocumentStatus.UPLOADING
  if (status === DocumentStatus.PENDING || status === DocumentStatus.EMBEDDING) return DocumentStatus.EMBEDDING
  if (status === DocumentStatus.EMBEDDED) return DocumentStatus.EMBEDDED
  if (status === DocumentStatus.FAILED) return DocumentStatus.FAILED
  return DocumentStatus.CANCELLED
}

export function mapApiMessage(m) {
  const cit = Array.isArray(m.citations) ? { sources: m.citations } : m.citations
  return {
    id: m.id,
    role: m.role,
    text: m.content,
    sources: cit?.sources || undefined,
    chunkIds: cit?.chunk_ids || undefined,
    confidence: cit?.confidence ?? undefined,
    confidenceLevel: cit?.confidence_level ?? undefined,
    rejected: cit?.rejected ?? undefined,
    signals: cit?.signals || undefined,
  }
}