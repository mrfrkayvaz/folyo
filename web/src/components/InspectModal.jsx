import { useEffect } from "react"
import { createPortal } from "react-dom"
import { CONFIDENCE_LEVELS } from "../constants/index.js"
import { DocIcon, XIcon } from "./icons.jsx"

function SignalMark({ ok }) {
  return ok ? (
    <span className="badge badge-success badge-xs">eşiği aştı</span>
  ) : (
    <span className="badge badge-error badge-xs">eşiği aşamadı</span>
  )
}

export default function InspectModal({ message: m, onClose }) {
  const chunkIds = m.chunkIds || []
  const sig = m.signals

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />

      <div className="relative z-10 flex max-h-[80vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-base-300 bg-base-100 shadow-2xl">
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
                className={`badge ${CONFIDENCE_LEVELS[m.confidenceLevel]?.cls ?? "badge-neutral"} badge-soft badge-sm`}
              >
                {m.confidenceLevel} · %{Math.round(m.confidence)}
              </span>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
              Adım 1 — İlk retrieve edilen chunk'lar
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
                Retrieve sonrası adayların skorları eşik altında kaldı — LLM'e chunk gönderilmedi. Detay aşağıda.
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

          <p className="text-[11px] text-base-content/40">Chunk içerikleri yakında burada gösterilecek.</p>
        </div>
      </div>
    </div>,
    document.body,
  )
}