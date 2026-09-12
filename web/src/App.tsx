import ChatMain from "./components/ChatMain"
import Composer from "./components/Composer"
import ConfirmModal from "./components/ConfirmModal"
import FileBar from "./components/FileBar"
import FilePreviewModal from "./components/preview/FilePreviewModal"
import Header from "./components/Header"
import Sidebar from "./components/Sidebar"
import { ACCEPTED_FILE_ATTR } from "./constants/index"
import { useAppState } from "./hooks/useAppState"

/** Görünüm iskeleti — tüm oturum düzenlemesi `useAppState` hook'undadır. */
export default function App() {
  const s = useAppState()

  return (
    <div className="flex h-dvh bg-base-100 text-base-content">
      <Sidebar
        workspaces={s.ws.workspaces}
        activeId={s.ws.activeWorkspaceId ?? s.ws.activeWorkspace?.id ?? null}
        onSelect={(id) => void s.openWorkspace(id)}
        onNew={s.newChat}
        onDelete={s.promptDeleteWorkspace}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          theme={s.theme}
          onToggleTheme={s.toggle}
          onBack={s.inWorkspace ? s.newChat : undefined}
          title={s.chatTitle}
        />

        {s.att.attachments.length > 0 && (
          <FileBar
            attachments={s.att.attachments}
            onRemove={s.att.removeAttachment}
            onPreview={s.setPreviewAttachment}
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
          <footer className="flex justify-center px-4 pb-4 pt-1 sm:px-6">
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