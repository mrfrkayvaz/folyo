import { useCallback, useEffect, useState } from "react"
import type { ReactNode } from "react"

interface PopupProps {
  onClose: () => void
  /** Kartın ek sınıfları (boyut/konum/dolgu görünüm bileşenleri verir). */
  className?: string
  /** true iken (örn. yükleniyor) hiçbir kapama yolu çalışmaz. */
  blockClose?: boolean
  /** `close` — kapamayı animasyonla gerçekleştiren fonksiyonu iç butonlara verir. */
  children: (close: () => void) => ReactNode
}

const EXIT_MS = 180

/**
 * Ortak açılır pencere kabuğu: karartma + kart.
 * Açılışta `folyo-fade-in`/`folyo-modal-pop`, kapanışta `folyo-fade-out`/
 * `folyo-modal-exit` oynar; animasyon bittikten sonra `onClose` çağrılır (unmount).
 * Escape ve karartma tıklaması da animasyonlu kapanır.
 */
export default function Popup({ onClose, className = "", blockClose = false, children }: PopupProps) {
  const [closing, setClosing] = useState(false)

  const close = useCallback(() => {
    if (blockClose || closing) return
    setClosing(true)
    window.setTimeout(onClose, EXIT_MS)
  }, [blockClose, closing, onClose])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") close()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [close])

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-xs sm:p-4 ${
        closing ? "folyo-fade-out" : "folyo-fade-in"
      }`}
    >
      <div className="fixed inset-0" onClick={close} aria-hidden="true" />
      <div className={`relative z-10 ${closing ? "folyo-modal-exit" : "folyo-modal-pop"} ${className}`}>
        {children(close)}
      </div>
    </div>
  )
}