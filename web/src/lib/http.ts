import { apiUrl } from "./apiBase"

export { apiUrl }

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

export async function jfetch<T = unknown>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(url), opts)
  if (!res.ok) throw new Error(await httpErrorMessage(res))
  return (await res.json()) as T
}