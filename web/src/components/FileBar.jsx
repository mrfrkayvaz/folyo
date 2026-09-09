import { DocIcon, XIcon } from "./icons.jsx"
import { formatBytes } from "../utils/formatters.js"
import { DocumentStatus } from "../enums/documentEnums.js"

export default function FileBar({ attachments, onRemove, onPreview }) {
  return (
    <div className="flex flex-wrap items-center justify-start gap-2 border-b border-base-300/40 bg-base-100 px-3 py-2 sm:px-4">
      {attachments.map((a) => {
        const busy = a.phase === "queued" || a.phase === DocumentStatus.UPLOADING || a.phase === DocumentStatus.EMBEDDING
        const removable = !busy
        const err = a.phase === DocumentStatus.FAILED
        return (
          <div
            key={a.key}
            onClick={() => onPreview?.(a)}
            className={`inline-flex cursor-pointer select-none min-w-0 items-center gap-2 rounded-xl border px-3 py-1.5 text-xs transition hover:border-primary/50 hover:bg-base-200 ${
              err ? "border-error/40 bg-error/5" : "border-base-300 bg-base-200/70"
            }`}
            title="Önizlemek için tıklayın"
          >
            <DocIcon className={`h-4 w-4 shrink-0 ${err ? "text-error" : "text-primary"}`} />
            <span className="flex min-w-0 flex-col">
              <span className="max-w-44 truncate font-medium text-base-content/90">
                {a.filename || a.file?.name}
                <span className="ml-1.5 text-[10px] font-normal text-base-content/40">
                  {formatBytes(a.size ?? a.file?.size)}
                </span>
              </span>
              <span className="flex items-center gap-1 text-[11px] text-base-content/50">
                {a.phase === "queued" && <span>sırada…</span>}
                {a.phase === DocumentStatus.UPLOADING && (
                  <>
                    <span className="loading loading-spinner loading-xs text-primary" />
                    <span>yükleniyor %{a.progress}</span>
                  </>
                )}
                {a.phase === DocumentStatus.EMBEDDING && (
                  <>
                    <span className="loading loading-spinner loading-xs text-primary" />
                    <span>taranıyor %{a.progress ?? "…"}</span>
                  </>
                )}
                {a.phase === DocumentStatus.EMBEDDED && <span className="text-success">✓ işlendi</span>}
                {err && <span className="text-error">{a.error || "işlenemedi"}</span>}
                {a.phase === DocumentStatus.CANCELLED && <span className="text-base-content/45">iptal</span>}
              </span>
            </span>
            {removable && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onRemove(a.key, a.docId)
                }}
                className="btn btn-circle btn-ghost h-5 w-5 min-h-5 shrink-0 text-base-content/50 hover:text-error"
                title="Kaldır"
                aria-label={`${a.filename || a.file?.name || "Dosya"} dosyasını kaldır`}
              >
                <XIcon className="h-3 w-3" />
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}