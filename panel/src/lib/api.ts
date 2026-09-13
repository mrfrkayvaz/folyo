/**
 * Backend adresi — `panel/.env` → `VITE_API_BASE_URL` (Vite, build sırasında okur).
 *
 * - Boş: aynı-origin `/api` kullanılır (dev: vite proxy · prod: Caddy /api proxy).
 * - Dolu (örn. `https://panel-api.folyo.app`): tüm istekler o adrese gider.
 *
 * Auth: store'daki token her isteğe `Authorization: Bearer` olarak eklenir;
 * 401 alınınca oturum temizlenir (App giriş ekranına döner).
 */
import type { DocumentDetailResponse, PanelWorkspace, WorkspaceDetailResponse } from "@/types/models"
import { useAuth } from "@/store/auth"

const API_BASE: string = String(import.meta.env.VITE_API_BASE_URL || "")
  .replace(/\/+$/, "")
  .replace(/\/api$/i, "")
const API_ROOT = API_BASE ? API_BASE + "/api" : "/api"

interface JFetchOptions {
  method?: string
  body?: unknown
}

async function jfetch<T>(path: string, opts: JFetchOptions = {}): Promise<T> {
  const token = useAuth.getState().token
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (opts.body !== undefined) headers["Content-Type"] = "application/json"

  const res = await fetch(API_ROOT + path, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  })

  if (res.status === 401 && !path.startsWith("/auth/login")) {
    useAuth.getState().logout()
    throw new Error("Oturum süresi doldu, tekrar giriş yapın.")
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data && typeof data.detail === "string") detail = data.detail
    } catch {
      /* JSON dışı hata gövdesi — generic hata mesajı yeterli */
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export interface WorkspacesResponse {
  workspaces: PanelWorkspace[]
}

export interface LoginResult {
  token: string
  username: string
  user_type: string
}

export const login = (username: string, password: string) =>
  jfetch<LoginResult>("/auth/login", { method: "POST", body: { username, password } })
export const authMe = () => jfetch<{ username: string; user_type: string }>("/auth/me")

export const listWorkspaces = () => jfetch<WorkspacesResponse>("/workspaces")
export const getWorkspace = (id: string) => jfetch<WorkspaceDetailResponse>(`/workspaces/${id}`)
export const getDocument = (id: string) => jfetch<DocumentDetailResponse>(`/documents/${id}`)