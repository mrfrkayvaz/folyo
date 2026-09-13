/**
 * Web oturum yönetimi (zustand + persist) — token localStorage'da kalıcıdır.
 * `lib/http.ts` her isteğe `Authorization: Bearer <token>` ekler; 401 → logout.
 */
import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AuthState {
  token: string | null
  username: string | null
  login: (token: string, username: string) => void
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,
      login: (token, username) => set({ token, username }),
      logout: () => set({ token: null, username: null }),
    }),
    { name: "folyo-web-auth" },
  ),
)