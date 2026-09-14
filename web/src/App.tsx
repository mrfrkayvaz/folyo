import { useEffect, useState } from "react"
import ChatMain from "./components/ChatMain"
import Composer from "./components/Composer"
import ConfirmModal from "./components/ConfirmModal"
import FileBar from "./components/FileBar"
import FilePreviewModal from "./components/preview/FilePreviewModal"
import Header from "./components/Header"
import Login from "./components/Login"
import Sidebar from "./components/Sidebar"
import { ACCEPTED_FILE_ATTR } from "./constants/index"
import { useAppState } from "./hooks/useAppState"
import { apiMe } from "./lib/http"
import { useAuth } from "./store/auth"

/**
 * Giriş kapısı: token yoksa Login. Token varsa ana görünüm (ChatApp) mount olur ve
 * `useAppState` ilk yüklemesini TAZE yapar (girişten ÖNCE workspace çekmez → ilk
 * girişte sohbetler boş kalmaz).
 */
export default function App() {
  const token = useAuth((s) => s.token)
  if (!token) {
    return <Login />
  }
  return <ChatApp />
}

function ChatApp() {
  const s = useAppState()
  const logout = useAuth((s) => s.logout)
  // Mobilde sidebar drawer olarak açılır (masaüstünde statik, davranış değişmez)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Oturum geri yükleme: stored token'ı sunucuda doğrula (geçersizse çıkış).
  useEffect(() => {
    apiMe().catch(() => useAuth.getState().logout())
  }, [])

  return (
    <div className="flex h-dvh bg-base-100 text-base-content">
      <Sidebar
        workspaces={s.ws.workspaces}
        activeId={s.ws.activeWorkspaceId ?? s.ws.activeWorkspace?.id ?? null}
        onSelect={(id) => {
          setSidebarOpen(false)
          void s.openWorkspace(id)
        }}
        onNew={() => {
          setSidebarOpen(false)
          s.newChat()
        }}
        onDelete={s.promptDeleteWorkspace}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          theme={s.theme}
          onToggleTheme={s.toggle}
          onMenu={() => setSidebarOpen(true)}
          onBack={s.inWorkspace ? s.newChat : undefined}
          title={s.chatTitle}
          onLogout={logout}
        />

        {s.att.attachments.length > 0 && (
          <FileBar
            attachments={s.att.attachments}
            onRemove={s.att.removeAttachment}
            onPreview={s.setPreviewAttachment}
            locked={s.chatStarted}
          />
        )}

        <ChatMain
          routeLoading={s.routeLoading}
          uploading={s.att.uploading}
          statusText={s.statusText}
          messages={s.chat.messages}
          onCitationClick={s.handleCitationClick}
          allReady={s.att.allReady}
          totalCount={s.att.totalCount}
          attachments={s.att.attachments}
          onAsk={s.handleSend}
          workspace={s.ws.activeWorkspace}
          onPickFile={s.pickFile}
          onDropFiles={s.handleDropFiles}
          olderAvailable={s.chat.olderAvailable}
          loadingOlder={s.chat.loadingOlder}
          onLoadOlder={() => void s.chat.loadOlder(s.ws.activeWorkspaceId ?? s.ws.activeWorkspace?.id)}
        />

        {s.showComposer && (
          <footer className="flex justify-center px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-1 sm:px-6">
            <Composer onSend={s.handleSend} busy={s.chat.busy} />
          </footer>
        )}

        <input
          ref={s.fileRef}
          type="file"
          accept={ACCEPTED_FILE_ATTR}
          multiple
          className="hidden"
          onChange={s.onFilePicked}
        />

        <ConfirmModal
          isOpen={Boolean(s.deleteTarget)}
          title="Sohbeti Sil"
          description={
            s.deleteTarget
              ? `"${s.deleteTarget.name}" başlıklı sohbet ve yüklenen tüm belgeler silinecektir. Bu işlem geri alınamaz.`
              : ""
          }
          confirmText="Sil"
          cancelText="Vazgeç"
          variant="danger"
          onClose={() => s.setDeleteTarget(null)}
          onConfirm={() => void s.confirmDeleteWorkspace()}
        />

        <FilePreviewModal attachment={s.previewAttachment} onClose={() => s.setPreviewAttachment(null)} />
      </div>
    </div>
  )
}