import { useEffect } from "react"
import { DocIcon, XIcon } from "../icons.jsx"
import { formatBytes } from "../../utils/formatters.js"
import { useFilePreview } from "../../hooks/useFilePreview.js"
import FileViewer from "./FileViewer.jsx"

export default function FilePreviewModal({ attachment, onClose }) {
  const preview = useFilePreview(attachment)

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && attachment) onClose()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [attachment, onClose])

  if (!attachment) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs transition-opacity animate-in fade-in duration-150 sm:p-6">
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />

      <div className="relative z-10 flex min-h-[300px] max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-base-300 bg-base-100 shadow-2xl">
        <div className="flex items-center justify-between border-b border-base-200 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5 pr-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <DocIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-base font-semibold tracking-tight text-base-content" title={preview.filename}>
                {preview.filename}
              </h3>
              {preview.size && (
                <p className="text-xs text-base-content/50">
                  {formatBytes(preview.size)}
                  {preview.targetPage ? ` · Sayfa ${preview.targetPage}` : ""}
                </p>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="btn btn-circle btn-ghost btn-sm text-base-content/60 hover:text-base-content"
            title="Kapat"
            aria-label="Kapat"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="flex min-h-[300px] flex-1 flex-col p-0">
          <FileViewer
            loading={preview.loading}
            error={preview.error}
            isPdf={preview.isPdf}
            isImage={preview.isImage}
            pdfUrl={preview.pdfUrl}
            imageUrl={preview.imageUrl}
            content={preview.content}
            filename={preview.filename}
            targetPage={preview.targetPage}
          />
        </div>
      </div>
    </div>
  )
}