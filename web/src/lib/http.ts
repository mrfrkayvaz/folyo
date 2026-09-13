import { apiUrl } from "./apiBase"
import { useAuth } from "../store/auth"

export { apiUrl }

/** Store'daki token'ı `Authorization: Bearer` olarak döndürür (isteğe bağlı header). */
export function authHeaders(): Record<string, string> {
  const token = useAuth.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function httpErrorMessage(res: Response): Promise<string> {
  let msg = `HTTP ${res.status}`
  try {
    const body = await res.json()
    if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
  } catch {
    /* yanıt JSON değilse durum kodu yeterli */
  }
  return msg
}

export async function jfetch<T = unknown>(url: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(apiUrl(url), {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers ?? {}) },
  })
  // Oturum sona erdi: dışında her 401'de temizle (giriş ekranına dön).
  // Not: login yolu tam şekliyle `/api/auth/login` gelir — `startsWith("/auth/login")`
  // eşleşmezdi; `includes` kullan. (Yanlış şifre → oturum temizlenmez, gerçek hata gösterilir.)
  if (res.status === 401 && !url.includes("/auth/login")) {
    useAuth.getState().logout()
    throw new Error("Oturum süresi doldu, tekrar giriş yapın.")
  }
  if (!res.ok) throw new Error(await httpErrorMessage(res))
  return (await res.json()) as T
}

export interface LoginResult {
  token: string
  username: string
  user_type: string
}

export const apiLogin = (username: string, password: string) =>
  jfetch<LoginResult>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })

export const apiMe = () => jfetch<{ username: string; user_type: string }>("/api/auth/me")