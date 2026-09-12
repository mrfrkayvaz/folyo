import { useEffect, useRef } from "react"
import MessageList from "./MessageList.jsx"
import ReadyState from "./ReadyState.jsx"
import UploadingState from "./UploadingState.jsx"
import Welcome from "./Welcome.jsx"

export default function ChatMain({
  routeLoading,
  uploading,
  statusText,
  messages,
  onCitationClick,
  allReady,
  totalCount,
  attachments,
  onAsk,
  workspace,
  onPickFile,
  onDropFiles,
  olderAvailable,
  loadingOlder,
  onLoadOlder,
}) {
  const mainRef = useRef(null)
  // En üstte eski mesaj yüklenince içeriğin boyu büyür; okuma konumunu korumak için
  // tetik anındaki "alt çapa" (scrollHeight − scrollTop) saklanır ve yeniden uygulanır.
  const bottomAnchor = useRef(null)

  const handleScroll = () => {
    const el = mainRef.current
    if (!el) return
    if (el.scrollTop <= 0 && olderAvailable && !loadingOlder) {
      bottomAnchor.current = el.scrollHeight - el.scrollTop
      onLoadOlder?.()
    }
  }

  useEffect(() => {
    const el = mainRef.current
    if (el && bottomAnchor.current != null) {
      el.scrollTop = Math.max(0, el.scrollHeight - bottomAnchor.current)
      bottomAnchor.current = null
    }
    // messages.length değiştiğinde (prepend) veya yükleme bittiğinde konumu geri yükle
  }, [messages.length, loadingOlder])

  return (
    <main ref={mainRef} onScroll={handleScroll} className="ctx-scroll min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 sm:px-6">
        {(olderAvailable || loadingOlder) && messages.length > 0 && (
          <div className="flex items-center justify-center gap-2 py-2 text-xs text-base-content/50">
            {loadingOlder ? (
              <>
                <span className="loading loading-spinner loading-xs" /> Eski mesajlar yükleniyor…
              </>
            ) : (
              "Daha eski mesajlar için yukarı kaydırın"
            )}
          </div>
        )}

        {routeLoading ? (
          <div className="flex flex-1 items-center justify-center py-24">
            <span className="loading loading-spinner loading-lg text-base-content/20" />
          </div>
        ) : uploading && messages.length === 0 ? (
          <UploadingState statusText={statusText} />
        ) : messages.length > 0 ? (
          <MessageList messages={messages} onCitationClick={onCitationClick} />
        ) : allReady ? (
          <ReadyState
            totalCount={totalCount}
            attachments={attachments}
            onAsk={onAsk}
            workspace={workspace}
          />
        ) : (
          <Welcome onPickFile={onPickFile} onDropFiles={onDropFiles} />
        )}
      </div>
    </main>
  )
}