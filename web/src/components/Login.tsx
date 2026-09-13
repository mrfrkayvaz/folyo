import { useState, type FormEvent } from "react"
import { apiLogin } from "../lib/http"
import { useAuth } from "../store/auth"

export default function Login() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const doLogin = useAuth((s) => s.login)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const res = await apiLogin(username.trim(), password)
      doLogin(res.token, res.username)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Giriş başarısız.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-base-200/50 p-4">
      <div className="card w-full max-w-sm border border-base-300/50 bg-base-100 shadow-xl">
        <div className="card-body gap-5">
          <div className="flex flex-col items-center gap-2 pb-1">
            <img src="/logo.svg" alt="Folyo" className="mx-auto h-20 w-auto" />
            <span className="text-xl font-semibold tracking-tight text-base-content">Folyo</span>
          </div>

          <form onSubmit={submit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-base-content/60">Kullanıcı adı</span>
              <input
                type="text"
                autoComplete="username"
                className="input input-bordered w-full"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-base-content/60">Şifre</span>
              <input
                type="password"
                autoComplete="current-password"
                className="input input-bordered w-full"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {error && (
              <p role="alert" className="rounded-xl border border-error/30 bg-error/10 px-3 py-2 text-sm text-error">
                {error}
              </p>
            )}

            <button type="submit" className="btn btn-primary mt-1" disabled={busy}>
              {busy ? (
                <>
                  <span className="loading loading-spinner loading-sm" />
                  Giriş yapılıyor…
                </>
              ) : (
                "Giriş Yap"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}