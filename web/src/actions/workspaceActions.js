import { jfetch } from "../lib/http.js"

export const createWorkspaceAction = () =>
  jfetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  })

export const listWorkspacesAction = () => jfetch("/api/workspaces")

export const getWorkspaceAction = (workspaceId) => jfetch(`/api/workspaces/${workspaceId}`)

export const olderMessagesAction = (workspaceId, { beforeAt, beforeId, limit = 10 } = {}) => {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (beforeAt) qs.set("before_at", beforeAt)
  if (beforeId) qs.set("before_id", beforeId)
  return jfetch(`/api/workspaces/${workspaceId}/messages?${qs}`)
}

export const chunksAction = (ids) => {
  const qs = new URLSearchParams({ ids: ids.join(",") })
  return jfetch(`/api/chunks?${qs}`)
}

export const deleteWorkspaceAction = (workspaceId) =>
  jfetch(`/api/workspaces/${workspaceId}`, { method: "DELETE" })
