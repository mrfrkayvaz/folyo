import { useEffect, useState } from "react"
import { createPortal } from "react-dom"
import { chunksAction } from "../actions/index"
import { CONFIDENCE_LEVELS } from "../constants/index"
import { DocIcon, XIcon } from "./icons"
import type { ChatMessageItem } from "../types/chatTypes"
import type { ChunkItem } from "../types/chunkTypes"

const SIGNAL_OK = "eşiği aştı"
const SIGNAL_FAIL = "eşiği aşamadı"

const TYPE_BADGE: Record<string, string> = {
  text: "badge-neutral",
  table: "badge-info",
  image: "badge-success",
  equation: "badge-warning",
  ocr_text: "badge-secondary",
  code: "badge-error",
}

function SignalMark({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="badge badge-success badge-xs">{SIGNAL_OK}</span>
  ) : (
    <span className="badge badge-error badge-xs">{SIGNAL_FAIL}</span>
  )
}

interface InspectModalProps {
  message: ChatMessageItem
  onClose: () => void
}

export default function InspectModal({ message: m, onClose }: InspectModalProps) {
  const chunkIds = m.chunkIds || []
  const sig = m.signals
  const [chunks, setChunks] = useState<ChunkItem[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [chunksError, setChunksError] = useState("")

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const idsKey = chunkIds.join(",")
  useEffect(() => {
    if (!chunkIds.length) return
    let cancelled = false
    setChunksLoading(true)
    setChunksError("")
    chunksAction(chunkIds)
      .then((data) => {
        if (!cancelled) setChunks(data.chunks || [])
      })
      .catch((err) => {
        if (!cancelled) setChunksError(err instanceof Error ? err.message : "Chunk içerikleri alınamadı.")
      })
      .finally(() => {
        if (!cancelled) setChunksLoading(false)
      })
    return () => {
      cancelled = true
    }
    // idsKey değişmedikçe tekrar çekme
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey])

  const byId = new Map(chunks.map((c) => [c.id, c]))

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />

      <div className="relative z-10 flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-base-300 bg-base-100 shadow-2xl">
        <div className="flex items-center justify-between border-b border-base-200 px-5 py-3">
          <h3 className="text-base font-semibold tracking-tight text-base-content">Yanıt incelemesi</h3>
          <button
            type="button"
            onClick={onClose}
            className="btn btn-circle btn-ghost btn-sm text-base-content/60 hover:text-base-content"
            aria-label="Kapat"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {m.confidence != null && (
            <div className="text-sm text-base-content/80">
              Güven rozeti:{" "}
              <span
                className={`badge ${(m.confidenceLevel && CONFIDENCE_LEVELS[m.confidenceLevel]?.cls) ?? "badge-neutral"} badge-soft badge-sm`}
              >
                {m.confidenceLevel ?? "–"} · %{Math.round(m.confidence)}
              </span>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
              Adım 1 — İlk retrieve edilen chunk&apos;lar
            </p>
            {chunkIds.length > 0 ? (
              <ul className="mt-2 flex flex-col gap-1.5">
                {chunkIds.map((id) => (
                  <li
                    key={id}
                    className="flex items-center gap-2 rounded-lg border border-base-300 bg-base-200/60 px-2.5 py-1.5 font-mono text-xs text-base-content/80"
                  >
                    <DocIcon className="h-3.5 w-3.5 shrink-0 text-primary" />
                    {id}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-base-content/50">
                Retrieve sonrası adayların skorları eşik altında kaldı — LLM&apos;e chunk gönderilmedi. Detay aşağıda.
              </p>
            )}
          </div>

          {sig && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
                Adım 2 — Güvenlik kalkanı (çift sinyal)
              </p>
              <ul className="mt-2 space-y-1.5 text-xs text-base-content/80">
                <li className="flex flex-wrap items-center gap-2 rounded-lg border border-base-300 bg-base-200/60 px-2.5 py-1.5">
                  <span className="font-medium">Dense kosinüs</span>
                  <span className="font-mono">{sig.dense}</span>
                  <span className="text-base-content/45">(eşik ≥ {sig.dense_min})</span>
                  <SignalMark ok={sig.dense >= sig.dense_min} />
                </li>
                <li className="flex flex-wrap items-center gap-2 rounded-lg border border-base-300 bg-base-200/60 px-2.5 py-1.5">
                  <span className="font-medium">BM25 ham</span>
                  <span className="font-mono">{sig.bm25}</span>
                  <span className="text-base-content/45">(eşik ≥ {sig.bm25_min})</span>
                  <SignalMark ok={sig.bm25 >= sig.bm25_min} />
                </li>
              </ul>
              {m.rejected && (
                <p className="mt-2 rounded-lg bg-warning/10 px-2.5 py-1.5 text-xs text-warning">
                  İki sinyal de eşiği aşamadı → kalkan devreye girdi, LLM çağrılmadı.
                </p>
              )}
            </div>
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
              Adım 3 — Chunk içerikleri
            </p>
            {chunksLoading ? (
              <div className="mt-2 flex items-center gap-2 text-xs text-base-content/50">
                <span className="loading loading-spinner loading-xs" /> Chunk içerikleri yükleniyor…
              </div>
            ) : chunksError ? (
              <p className="mt-2 rounded-lg bg-error/10 px-2.5 py-1.5 text-xs text-error">{chunksError}</p>
            ) : chunkIds.length === 0 ? (
              <p className="mt-2 text-xs text-base-content/50">Bu yanıtta chunk gönderilmedi.</p>
            ) : (
              <div className="mt-2 flex flex-col gap-2">
                {chunkIds.map((id) => {
                  const c = byId.get(id)
                  if (!c)
                    return (
                      <div
                        key={id}
                        className="rounded-lg border border-dashed border-base-300 bg-base-200/40 px-2.5 py-2 font-mono text-xs text-base-content/50"
                      >
                        {id} — chunk bulunamadı (silinmiş olabilir)
                      </div>
                    )
                  return (
                    <div key={id} className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="font-mono text-base-content/70">{c.name || c.doc_id?.slice(0, 8)}</span>
                        <span className="text-base-content/50">parça {c.chunk_index + 1}</span>
                        <span className="text-base-content/50">sayfa {c.page_number}</span>
                        <span className={`badge ${TYPE_BADGE[c.content_type] || "badge-neutral"} badge-xs`}>
                          {c.content_type}
                        </span>
                        {c.section_title && (
                          <span className="max-w-[50%] truncate text-base-content/50">{c.section_title}</span>
                        )}
                        {c.image_path && (
                          <span className="badge badge-outline badge-xs font-mono">{c.image_path}</span>
                        )}
                      </div>
                      <p className="mt-1.5 max-h-48 overflow-y-auto whitespace-pre-wrap rounded bg-base-300/40 p-2 font-mono text-[11.5px] leading-5 text-base-content/85">
                        {c.text}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}