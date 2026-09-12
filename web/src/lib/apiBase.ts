/**
 * Backend adresi — `web/.env` → `VITE_API_BASE_URL` (Vite, build sırasında okur).
 *
 * - Boş: aynı-origin `/api` kullanılır (dev: vite proxy · prod: Caddy /api proxy).
 * - Dolu (örn. `https://api.folyo.app`): tüm istekler o adrese gider.
 */
export const API_BASE: string = String(import.meta.env.VITE_API_BASE_URL || "")
  .replace(/\/+$/, "")
  .replace(/\/api$/i, "")

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`
  return API_BASE ? `${API_BASE}${p}` : p
}