import { jfetch } from "../lib/http.js"

export const createWorkspaceAction = () =>
  jfetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  })

export const listWorkspacesAction = () => jfetch("/api/workspaces")

export const getWorkspaceAction = (workspaceId) => jfetch(`/api/workspaces/${workspaceId}`)

export const deleteWorkspaceAction = (workspaceId) =>
  jfetch(`/api/workspaces/${workspaceId}`, { method: "DELETE" })
