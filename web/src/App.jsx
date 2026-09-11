import { useEffect, useRef, useState } from "react"
import ChatMain from "./components/ChatMain.jsx"
import Composer from "./components/Composer.jsx"
import ConfirmModal from "./components/ConfirmModal.jsx"
import FileBar from "./components/FileBar.jsx"
import FilePreviewModal from "./components/preview/FilePreviewModal.jsx"
import Header from "./components/Header.jsx"
import Sidebar from "./components/Sidebar.jsx"
import { getWorkspaceAction } from "./actions/index.js"
import { ACCEPTED_FILE_ATTR } from "./constants/index.js"
import { DocumentStatus } from "./enums/index.js"
import { mapDocPhase, terminalPhase } from "./lib/helpers.js"
import { useAttachments } from "./hooks/useAttachments.js"
import { useChatMessages } from "./hooks/useChatMessages.js"
import { useTheme } from "./hooks/useTheme.js"
import { useWorkspacesStore } from "./stores/workspacesStore.js"

const WS_ROUTE = /^\/workspace\/([^/]+)/

export default function App() {
  const { theme, toggle } = useTheme()
  const ws = useWorkspacesStore()
  const chat = useChatMessages()
  const att = useAttachments(ws.openWorkspace)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [previewAttachment, setPreviewAttachment] = useState(null)
  const fileRef = useRef(null)

  const routeMatch = window.location.pathname.match(WS_ROUTE)
  const [routeLoading, setRouteLoading] = useState(Boolean(routeMatch))

  const inWorkspace = Boolean(ws.activeWorkspaceId || ws.activeWorkspace)
  const chatStarted = chat.chatStarted
  const showComposer = !att.hasFailed && ((att.totalCount > 0 && !att.uploading) || chatStarted)

  // ----- Yaşam döngüsü: ilk yükleme + tarayıcı geçmişi -----
  useEffect(() => {
    ws.hydrate()

    const match = window.location.pathname.match(WS_ROUTE)
    if (match) openWorkspace(match[1], { pushUrl: false })

    const handlePopState = () => {
      const m = window.location.pathname.match(WS_ROUTE)
      if (m) openWorkspace(m[1], { pushUrl: false })
      else newChat({ pushUrl: false })
    }
    window.addEventListener("popstate", handlePopState)

    return () => {
      window.removeEventListener("popstate", handlePopState)
      att.stopPolling()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ----- Oturum: yeni sohbet / workspace aç -----
  const newChat = (opts = {}) => {
    const pushUrl = opts?.pushUrl ?? true
    if (pushUrl && window.location.pathname !== "/") {
      window.history.pushState(null, "", "/")
    }
    att.reset()
    chat.reset()
    ws.goHome()
    setRouteLoading(false)
  }

  const openWorkspace = async (id, opts = {}) => {
    const pushUrl = opts?.pushUrl ?? true
    if (pushUrl && window.location.pathname !== `/workspace/${id}`) {
      window.history.pushState(null, "", `/workspace/${id}`)
    }
    ws.openWorkspace(id)
    att.reset()
    chat.reset()
    setRouteLoading(true)
    try {
      const d = await getWorkspaceAction(id)
      ws.openWorkspace(d.workspace || d)
      const docs = d.documents || []
      if (docs.length) {
        att.setFromDocuments(docs)
        if (docs.some((doc) => !terminalPhase(mapDocPhase(doc.status)))) att.startPolling(id)
      }
      chat.setFromApi(d.messages)
    } catch {
      window.history.replaceState(null, "", "/")
      ws.goHome()
    } finally {
      setRouteLoading(false)
    }
  }

  // ----- Seçimler & ek işlemler -----
  const handleSend = (rawText) => {
    if (chat.busy) return
    chat.ask(rawText)
  }

  const handleCitationClick = ({ filename, pageNumber, chunkIndex }) => {
    if (!filename) return
    const targetName = filename.trim().toLowerCase()
    const found = att.attachments.find((a) => {
      const fn = (a.filename || a.file?.name || "").trim().toLowerCase()
      return fn === targetName || fn.includes(targetName) || targetName.includes(fn)
    })
    if (found) setPreviewAttachment({ ...found, targetChunk: chunkIndex, targetPage: pageNumber })
  }

  const promptDeleteWorkspace = (id) => {
    const targetWs = ws.workspaces.find((w) => w.id === id)
    setDeleteTarget({ id, name: targetWs?.name || "Bu sohbet" })
  }

  const confirmDeleteWorkspace = async () => {
    if (!deleteTarget) return
    const id = deleteTarget.id
    setDeleteTarget(null)
    const wasActive = ws.activeWorkspaceId === id || ws.activeWorkspace?.id === id
    await ws.removeWorkspace(id)
    if (wasActive) newChat()
  }

  // ----- Dosya seçimi -----
  const pickFile = () => {
    if (chatStarted) return
    fileRef.current?.click()
  }

  const onFilePicked = (e) => {
    const input = e.target
    const files = [...(input.files || [])]
    input.value = ""
    if (!files.length || chatStarted) return
    att.acceptFiles(files)
  }

  const handleDropFiles = (files) => {
    if (!files?.length || chatStarted) return
    att.acceptFiles(files)
  }

  // ----- Görünüm türevleri -----
  const updCount = att.attachments.filter((a) => a.phase === DocumentStatus.UPLOADING).length
  const embCount = att.attachments.filter((a) => a.phase === DocumentStatus.EMBEDDING).length
  let statusText = "belgeler hazırlanıyor…"
  if (updCount && embCount) statusText = `${updCount} dosya yükleniyor · ${embCount} dosya taranıyor`
  else if (updCount) statusText = `${updCount} dosya yükleniyor…`
  else if (embCount) statusText = `${embCount} dosya taranıyor ve indeksleniyor…`
  if (att.doneCount > 0) statusText = `${att.doneCount}/${att.totalCount} işlendi · ${statusText}`

  const chatTitle = ws.activeWorkspace?.name?.trim() || (inWorkspace ? "Yeni sohbet" : "")

  return (
    <div className="flex h-dvh bg-base-100 text-base-content">
      <Sidebar
        workspaces={ws.workspaces}
        activeId={ws.activeWorkspaceId ?? ws.activeWorkspace?.id ?? null}
        onSelect={openWorkspace}
        onNew={newChat}
        onDelete={promptDeleteWorkspace}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          theme={theme}
          onToggleTheme={toggle}
          onBack={inWorkspace ? newChat : undefined}
          title={chatTitle}
        />

        {att.attachments.length > 0 && (
          <FileBar
            attachments={att.attachments}
            onRemove={att.removeAttachment}
            onPreview={setPreviewAttachment}
          />
        )}

        <ChatMain
          routeLoading={routeLoading}
          uploading={att.uploading}
          statusText={statusText}
          messages={chat.messages}
          onCitationClick={handleCitationClick}
          allReady={att.allReady}
          totalCount={att.totalCount}
          attachments={att.attachments}
          onAsk={handleSend}
          workspace={ws.activeWorkspace}
          onPickFile={pickFile}
          onDropFiles={handleDropFiles}
        />

        {showComposer && (
          <footer className="flex justify-center px-4 pb-4 pt-1 sm:px-6">
            <Composer onSend={handleSend} busy={chat.busy} />
          </footer>
        )}

        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED_FILE_ATTR}
          multiple
          className="hidden"
          onChange={onFilePicked}
        />

        <ConfirmModal
          isOpen={Boolean(deleteTarget)}
          title="Sohbeti Sil"
          description={
            deleteTarget
              ? `"${deleteTarget.name}" başlıklı sohbet ve yüklenen tüm belgeler silinecektir. Bu işlem geri alınamaz.`
              : ""
          }
          confirmText="Sil"
          cancelText="Vazgeç"
          variant="danger"
          onClose={() => setDeleteTarget(null)}
          onConfirm={confirmDeleteWorkspace}
        />

        <FilePreviewModal attachment={previewAttachment} onClose={() => setPreviewAttachment(null)} />
      </div>
    </div>
  )
}