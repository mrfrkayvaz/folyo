import { useEffect } from "react"

/**
 * Genel kullanım için yeniden kullanılabilir onay modalı (Popup).
 */
export default function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = "Emin misiniz?",
  description = "Bu işlemi gerçekleştirmek istediğinize emin misiniz?",
  confirmText = "Sil",
  cancelText = "Vazgeç",
  variant = "danger",
  loading = false,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen && !loading) {
        onClose()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, loading, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs transition-opacity animate-in fade-in duration-150">
      {/* Arka plan overlay */}
      <div className="fixed inset-0" onClick={() => !loading && onClose()} aria-hidden="true" />

      {/* Modal Kutusu */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-6 shadow-2xl transition-all">
        <h3 className="text-lg font-semibold tracking-tight text-base-content">{title}</h3>
        {description && (
          <p className="mt-2 text-sm leading-relaxed text-base-content/70">{description}</p>
        )}

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="btn btn-ghost px-4 text-sm font-medium"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={`btn px-4 text-sm font-medium ${
              variant === "danger"
                ? "btn-error text-white"
                : "btn-primary"
            }`}
          >
            {loading && <span className="loading loading-spinner loading-xs" />}
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
