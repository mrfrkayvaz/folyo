import { jfetch } from "../lib/http"
import type { ApiMessage } from "../types/chatTypes"
import type { ChunkItem } from "../types/chunkTypes"
import type { DocumentItem } from "../types/documentTypes"
import type { Workspace } from "../types/workspaceTypes"

export interface WorkspaceListResponse {
  workspaces: Workspace[]
}

export interface WorkspaceDetailResponse {
  workspace?: Workspace
  documents?: DocumentItem[]
  messages?: ApiMessage[]
  has_more?: boolean
}

export interface OlderMessagesResponse {
  messages: ApiMessage[]
  has_more?: boolean
}

export interface ChunksResponse {
  chunks: ChunkItem[]
  found?: number
}

export const createWorkspaceAction = (): Promise<Workspace> =>
  jfetch<Workspace>("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  })

export const listWorkspacesAction = (): Promise<WorkspaceListResponse> =>
  jfetch<WorkspaceListResponse>("/api/workspaces")

export const getWorkspaceAction = (workspaceId: string): Promise<WorkspaceDetailResponse> =>
  jfetch<WorkspaceDetailResponse>(`/api/workspaces/${workspaceId}`)

export interface OlderMessagesParams {
  beforeAt: string
  beforeId: string
  limit?: number
}

export const olderMessagesAction = (
  workspaceId: string,
  { beforeAt, beforeId, limit = 10 }: OlderMessagesParams,
): Promise<OlderMessagesResponse> => {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (beforeAt) qs.set("before_at", beforeAt)
  if (beforeId) qs.set("before_id", beforeId)
  return jfetch<OlderMessagesResponse>(`/api/workspaces/${workspaceId}/messages?${qs}`)
}

export const chunksAction = (ids: string[]): Promise<ChunksResponse> => {
  const qs = new URLSearchParams({ ids: ids.join(",") })
  return jfetch<ChunksResponse>(`/api/chunks?${qs}`)
}

export const deleteWorkspaceAction = (workspaceId: string): Promise<unknown> =>
  jfetch(`/api/workspaces/${workspaceId}`, { method: "DELETE" })