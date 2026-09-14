import { useEffect } from "react"
import Popup from "./Popup"

interface ConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: "danger" | "primary"
  loading?: boolean
}

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
}: ConfirmModalProps) {
  if (!isOpen) return null

  return (
    <Popup
      onClose={() => !loading && onClose()}
      blockClose={loading}
      className="w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-6 shadow-2xl"
    >
      {(close) => (
        <>
          <h3 className="text-lg font-semibold tracking-tight text-base-content">{title}</h3>
          {description && (
            <p className="mt-2 text-sm leading-relaxed text-base-content/70">{description}</p>
          )}

          <div className="mt-6 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={close}
              disabled={loading}
              className="btn btn-ghost px-4 text-sm font-medium"
            >
              {cancelText}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={loading}
              className={`btn px-4 text-sm font-medium ${variant === "danger" ? "btn-error text-white" : "btn-primary"}`}
            >
              {loading && <span className="loading loading-spinner loading-xs" />}
              {confirmText}
            </button>
          </div>
        </>
      )}
    </Popup>
  )
}