import { useCallback, useEffect, useState } from "react"
import { listQaLogs } from "@/lib/api"
import { formatTs } from "@/utils/formatters"
import type { QaLogsResponse } from "@/types/models"

type LevelFilter = "" | "info" | "warning" | "error"

const LEVEL_BADGE: Record<string, string> = {
  info: "badge-info",
  warning: "badge-warning",
  error: "badge-error",
}

const LEVEL_LABEL: Record<string, string> = {
  info: "bilgi",
  warning: "uyarı",
  error: "hata",
}

const PAGE_SIZE = 30
const REFRESH_MS = 6000 // canlı takip: yeni QA istekleri kendiliğinden görünür

export default function QaLogsView() {
  const [data, setData] = useState<QaLogsResponse | null>(null)
  const [page, setPage] = useState(1)
  const [level, setLevel] = useState<LevelFilter>("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (targetPage: number, targetLevel: LevelFilter) => {
    setLoading(true)
    setError(null)
    try {
      const res = await listQaLogs({ page: targetPage, limit: PAGE_SIZE, level: targetLevel || undefined })
      setData(res)
      // Sayfa boşaldıysa geri çek (silme/filtre sonrası)
      if (res.pages > 0 && targetPage > res.pages) setPage(res.pages)
    } catch {
      setError("Loglar getirilemedi.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(page, level)
  }, [page, level, load])

  // Canlı takip — panel açıkken yeni sahne logları otomatik akar
  useEffect(() => {
    const t = setInterval(() => void load(page, level), REFRESH_MS)
    return () => clearInterval(t)
  }, [page, level, load])

  const changeLevel = (l: LevelFilter) => {
    setLevel(l)
    setPage(1)
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const pages = Math.max(1, data?.pages ?? 1)

  return (
    <main className="ctx-scroll flex min-w-0 flex-1 flex-col overflow-y-auto">
      <div className="flex items-center gap-3 border-b border-base-300/40 px-5 py-4">
        <div>
          <h1 className="text-base font-semibold">Cevap Logları</h1>
          <p className="text-xs text-base-content/45">Yanıt üretim aşamaları</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <select
            value={level}
            onChange={(e) => changeLevel(e.target.value as LevelFilter)}
            className="select select-sm w-32"
            aria-label="Seviye filtresi"
          >
            <option value="">Tümü</option>
            <option value="info">Bilgi</option>
            <option value="warning">Uyarı</option>
            <option value="error">Hata</option>
          </select>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={() => void load(page, level)}
            title="Yenile"
          >
            <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
          </button>
        </div>
      </div>

      {error && <p className="px-5 py-3 text-xs text-error">{error}</p>}

      <div className="flex flex-col gap-1.5 p-5 pt-4">
        {loading && items.length === 0 && (
          <p className="flex items-center gap-2 text-xs text-base-content/45">
            <span className="loading loading-spinner loading-xs text-primary" /> Yükleniyor…
          </p>
        )}
        {!loading && items.length === 0 && (
          <p className="text-xs text-base-content/40">
            Henüz cevap logu yok. Bir sohbette soru sorduğunda aşama kayıtları burada görünür.
          </p>
        )}
        {items.map((l) => (
          <div
            key={l.id}
            className="flex items-start gap-3 rounded-xl border border-base-300 bg-base-100 px-3 py-2"
          >
            <span className={`badge badge-sm mt-0.5 shrink-0 ${LEVEL_BADGE[l.level] ?? "badge-neutral"}`}>
              {LEVEL_LABEL[l.level] ?? l.level}
            </span>
            <span className="badge badge-outline badge-sm mt-0.5 shrink-0 font-mono text-base-content/60">
              {l.stage || "—"}
            </span>
            <div className="min-w-0 flex-1">
              <p className={`break-words whitespace-pre-wrap text-sm leading-5 ${l.level === "error" ? "text-error" : "text-base-content/85"}`}>
                {l.message}
              </p>
              <p className="mt-0.5 break-all font-mono text-[10px] text-base-content/35">
                {l.workspace_name || "—"} <span className="text-base-content/25">({l.workspace_id})</span>{" "}
                {l.created_at ? `· ${formatTs(l.created_at)}` : ""}
              </p>
            </div>
          </div>
        ))}

        {items.length > 0 && (
          <div className="mt-3 flex items-center justify-between border-t border-base-300/40 pt-3 text-xs text-base-content/55">
            <span>
              Sayfa {data?.page ?? 1} / {pages} · {total} kayıt
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={(data?.page ?? 1) <= 1}
                className="btn btn-sm btn-ghost"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ‹ Geri
              </button>
              <button
                type="button"
                disabled={(data?.page ?? 1) >= pages}
                className="btn btn-sm btn-ghost"
                onClick={() => setPage((p) => p + 1)}
              >
                İleri ›
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}