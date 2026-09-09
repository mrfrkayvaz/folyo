import { useEffect, useState } from "react"
import { DocIcon, XIcon } from "./icons.jsx"
import { formatBytes } from "../utils/formatters.js"
import { getDocumentFileUrlAction } from "../actions/documentActions.js"

/**
 * Üst bar veya listedeki dosyalara tıklandığında açılan
 * temiz dosya önizleme modalı.
 */
export default function FilePreviewModal({ attachment, onClose }) {
  const [content, setContent] = useState(null)
  const [pdfUrl, setPdfUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const filename = attachment?.filename || attachment?.file?.name || "Dosya"
  const size = attachment?.size ?? attachment?.file?.size
  const isPdf = filename.toLowerCase().endsWith(".pdf")

  useEffect(() => {
    if (!attachment) return

    let isMounted = true
    let createdUrl = null

    const loadContent = async () => {
      setLoading(true)
      setError(null)
      setContent(null)
      setPdfUrl(null)

      try {
        // 1. Yerel istemci tarafında yüklenmiş File nesnesi varsa
        if (attachment.file) {
          if (isPdf) {
            createdUrl = URL.createObjectURL(attachment.file)
            if (isMounted) setPdfUrl(createdUrl)
          } else {
            const text = await attachment.file.text()
            if (isMounted) setContent(text)
          }
        }
        // 2. Sunucuda kayıtlı belge id'si (docId) varsa
        else if (attachment.docId) {
          const res = await fetch(getDocumentFileUrlAction(attachment.docId))
          if (!res.ok) {
            throw new Error(`Dosya içeriği alınamadı (HTTP ${res.status})`)
          }

          if (isPdf) {
            const blob = await res.blob()
            createdUrl = URL.createObjectURL(blob)
            if (isMounted) setPdfUrl(createdUrl)
          } else {
            const text = await res.text()
            if (isMounted) setContent(text)
          }
        } else {
          throw new Error("Dosya içeriğine erişilemedi.")
        }
      } catch (err) {
        if (isMounted) setError(err.message || "İçerik yüklenirken bir hata oluştu.")
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    loadContent()

    return () => {
      isMounted = false
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl)
      }
    }
  }, [attachment, isPdf])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && attachment) {
        onClose()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [attachment, onClose])

  if (!attachment) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 sm:p-6 backdrop-blur-xs transition-opacity animate-in fade-in duration-150">
      {/* Arka plan overlay */}
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />

      {/* Önizleme Modal Kartı */}
      <div className="relative z-10 flex max-h-[85vh] w-full max-w-4xl flex-col rounded-2xl border border-base-300 bg-base-100 shadow-2xl overflow-hidden">
        {/* Üst Başlık Barı */}
        <div className="flex items-center justify-between px-4 py-3 sm:px-6 border-b border-base-200">
          <div className="flex items-center gap-2.5 min-w-0 pr-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <DocIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-base font-semibold tracking-tight text-base-content" title={filename}>
                {filename}
              </h3>
              {size && (
                <p className="text-xs text-base-content/50">
                  {formatBytes(size)}
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

        {/* Gövde / İçerik Alanı */}
        <div className="flex-1 overflow-y-auto p-0 flex flex-col">
          {loading ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3 text-center p-4 sm:p-6">
              <span className="loading loading-spinner loading-md text-primary" />
              <p className="text-xs text-base-content/50">Dosya yükleniyor…</p>
            </div>
          ) : error ? (
            <div className="flex h-64 flex-col items-center justify-center gap-2 text-center text-error p-4 sm:p-6">
              <p className="text-sm font-medium">⚠️ {error}</p>
            </div>
          ) : isPdf && pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="h-[75vh] w-full border-0 bg-base-200 block"
              title={filename}
            />
          ) : (
            <pre className="whitespace-pre-wrap break-words font-mono text-xs sm:text-sm leading-relaxed text-base-content/90 bg-base-200/50 p-4 sm:p-6 overflow-x-auto border-0 rounded-none m-0">
              {content}
            </pre>
          )}
        </div>

      </div>
    </div>
  )
}
