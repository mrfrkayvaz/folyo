import { apiUrl, jfetch } from "../lib/http"
import type { DocumentItem } from "../types/documentTypes"

export interface UploadResult {
  id: string
  status: string
}

/** Backend'e dosya yükleme — modern `fetch` ile (XMLHttpRequest yok). */
export async function uploadDocumentAction(workspaceId: string, file: File): Promise<UploadResult> {
  const url = apiUrl(
    `/api/workspaces/${workspaceId}/documents?size=${file.size}&filename=${encodeURIComponent(file.name)}`,
  )
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/octet-stream",
      "X-Filename": encodeURIComponent(file.name),
    },
    body: file,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => "")
    throw new Error(msg.slice(0, 200) || `HTTP ${res.status}`)
  }
  return (await res.json()) as UploadResult
}

export const getDocumentStatusAction = (documentId: string): Promise<DocumentItem> =>
  jfetch<DocumentItem>(`/api/documents/${documentId}`)

export const cancelDocumentAction = (documentId: string): Promise<unknown> =>
  jfetch(`/api/documents/${documentId}/cancel`, { method: "POST" })

export const deleteDocumentAction = (documentId: string): Promise<unknown> =>
  jfetch(`/api/documents/${documentId}`, { method: "DELETE" })

export const getDocumentFileUrlAction = (documentId: string): string =>
  apiUrl(`/api/documents/${documentId}/file`)