/**
 * Backend adresi — `panel/.env` → `VITE_API_BASE_URL` (Vite, build sırasında okur).
 *
 * - Boş: aynı-origin `/api` kullanılır (dev: vite proxy · prod: Caddy /api proxy).
 * - Dolu (örn. `https://panel-api.folyo.app`): tüm istekler o adrese gider.
 */
import type { DocumentDetailResponse, PanelWorkspace, WorkspaceDetailResponse } from "../types/models"

const API_BASE: string = String(import.meta.env.VITE_API_BASE_URL || "")
  .replace(/\/+$/, "")
  .replace(/\/api$/i, "")
const API_ROOT = API_BASE ? API_BASE + "/api" : "/api"

async function jfetch<T>(path: string): Promise<T> {
  const res = await fetch(API_ROOT + path)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

export interface WorkspacesResponse {
  workspaces: PanelWorkspace[]
}

export const listWorkspaces = () => jfetch<WorkspacesResponse>("/workspaces")
export const getWorkspace = (id: string) => jfetch<WorkspaceDetailResponse>(`/workspaces/${id}`)
export const getDocument = (id: string) => jfetch<DocumentDetailResponse>(`/documents/${id}`)