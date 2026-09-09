import { useEffect, useRef, useState } from "react"
import Header from "./components/Header.jsx"
import Sidebar from "./components/Sidebar.jsx"
import Welcome from "./components/Welcome.jsx"
import MessageList from "./components/MessageList.jsx"
import Composer from "./components/Composer.jsx"
import FileBar from "./components/FileBar.jsx"
import ConfirmModal from "./components/ConfirmModal.jsx"
import FilePreviewModal from "./components/FilePreviewModal.jsx"
import UploadingState from "./components/UploadingState.jsx"
import ReadyState from "./components/ReadyState.jsx"

import {
  askQAAction,
  deleteDocumentAction,
  getWorkspaceAction,
  uploadDocumentXHRAction,
} from "./actions/index.js"
import { DocumentStatus } from "./enums/index.js"
import { THEME_KEY } from "./constants/index.js"
import { useWorkspacesStore } from "./stores/workspacesStore.js"

const ALLOWED_EXTS = /^([^.]+\.)?(pdf|txt|md)$/i
let idCounter = 0
const nid = () => `m${++idCounter}`
let attachKey = 0
const aid = () => `a${++attachKey}`

function terminalPhase(p) {
  return p === DocumentStatus.EMBEDDED || p === DocumentStatus.FAILED || p === DocumentStatus.CANCELLED
}

function mapDocPhase(status) {
  if (status === DocumentStatus.UPLOADING) return DocumentStatus.UPLOADING
  if (status === DocumentStatus.PENDING || status === DocumentStatus.EMBEDDING) return DocumentStatus.EMBEDDING
  if (status === DocumentStatus.EMBEDDED) return DocumentStatus.EMBEDDED
  if (status === DocumentStatus.FAILED) return DocumentStatus.FAILED
  return DocumentStatus.CANCELLED
}

export default function App() {
  const [theme, setTheme] = useState(() => {
    try {
      const q = new URLSearchParams(location.search).get("theme")
      return q || localStorage.getItem(THEME_KEY) || "gemlight"
    } catch {
      return "gemlight"
    }
  })
  const ws = useWorkspacesStore()
  const [messages, setMessages] = useState([])
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [previewAttachment, setPreviewAttachment] = useState(null)
  const [attachments, setAttachments] = useState([])
  const fileRef = useRef(null)
  const uploadHandles = useRef(new Set())
  const pollRef = useRef(null)
  const pollWidRef = useRef(null)
  const attachRef = useRef([])

  const inWorkspace = Boolean(ws.activeWorkspaceId || ws.activeWorkspace)
  const busy = messages.some((m) => m.streaming)
  const chatStarted = messages.length > 0

  const uploading = attachments.some((a) => a.phase === DocumentStatus.UPLOADING || a.phase === DocumentStatus.EMBEDDING)
  const hasFailed = attachments.some((a) => a.phase === DocumentStatus.FAILED)
  const doneCount = attachments.filter((a) => a.phase === DocumentStatus.EMBEDDED).length
  const totalCount = attachments.length
  const allReady = totalCount > 0 && doneCount === totalCount
  const showComposer = !hasFailed && ((totalCount > 0 && !uploading) || chatStarted)

  const patchAttach = (key, patch) =>
    setAttachments((prev) => {
      const next = prev.map((a) => (a.key === key ? { ...a, ...patch } : a))
      attachRef.current = next
      return next
    })

  const setAttachmentsBoth = (updater) =>
    setAttachments((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater
      attachRef.current = next
      return next
    })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {}
  }, [theme])

  useEffect(() => {
    ws.hydrate()

    const match = window.location.pathname.match(/^\/workspace\/([^/]+)/)
    if (match) {
      openWorkspace(match[1], { pushUrl: false })
    }

    const handlePopState = () => {
      const m = window.location.pathname.match(/^\/workspace\/([^/]+)/)
      if (m) {
        openWorkspace(m[1], { pushUrl: false })
      } else {
        newChat({ pushUrl: false })
      }
    }

    window.addEventListener("popstate", handlePopState)

    return () => {
      window.removeEventListener("popstate", handlePopState)
      stopStatusPolling()
      for (const h of uploadHandles.current) h.abort()
      uploadHandles.current.clear()
    }
  }, [])

  const stopStatusPolling = () => {
    clearInterval(pollRef.current)
    pollRef.current = null
    pollWidRef.current = null
  }

  const startStatusPolling = (wid) => {
    if (pollWidRef.current === wid && pollRef.current) return
    stopStatusPolling()
    pollWidRef.current = wid
    pollRef.current = setInterval(async () => {
      const widNow = pollWidRef.current
      if (!widNow) return
      try {
        const d = await getWorkspaceAction(widNow)
        const docs = new Map((d.documents || []).map((x) => [x.id, x]))
        setAttachments((prev) => {
          let changed = false
          const next = prev.map((a) => {
            if (!a.docId) return a
            const doc = docs.get(a.docId)
            if (!doc) return a
            const phase = mapDocPhase(doc.status)
            if (phase === a.phase) return a
            changed = true
            return { ...a, phase, error: doc.error ?? undefined, progress: undefined }
          })
          attachRef.current = changed ? next : prev
          return changed ? next : prev
        })
        if (attachRef.current.every((a) => terminalPhase(a.phase))) stopStatusPolling()
      } catch {}
    }, 1500)
  }

  const resetSession = () => {
    stopStatusPolling()
    for (const h of uploadHandles.current) h.abort()
    uploadHandles.current.clear()
    setAttachmentsBoth([])
  }

  const newChat = (opts = {}) => {
    const pushUrl = opts?.pushUrl ?? true
    if (pushUrl && window.location.pathname !== "/") {
      window.history.pushState(null, "", "/")
    }
    resetSession()
    ws.goHome()
    setMessages([])
  }

  const openWorkspace = async (id, opts = {}) => {
    const pushUrl = opts?.pushUrl ?? true
    if (pushUrl && window.location.pathname !== `/workspace/${id}`) {
      window.history.pushState(null, "", `/workspace/${id}`)
    }
    ws.openWorkspace(id)
    resetSession()
    setMessages([])
    try {
      const d = await getWorkspaceAction(id)
      const wObj = d.workspace || d
      ws.openWorkspace(wObj)
      const docs = d.documents || []
      if (docs.length) {
        setAttachmentsBoth(
          docs.map((doc) => ({
            key: aid(),
            docId: doc.id,
            filename: doc.filename,
            size: doc.size,
            phase: mapDocPhase(doc.status),
            error: doc.error ?? undefined,
          })),
        )
        if (docs.some((doc) => !terminalPhase(mapDocPhase(doc.status)))) startStatusPolling(id)
      }
      setMessages(
        (d.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          text: m.content,
          sources: m.citations || undefined,
        })),
      )
    } catch {
      window.history.replaceState(null, "", "/")
      ws.goHome()
    }
  }

  const promptDeleteWorkspace = (id) => {
    const targetWs = ws.workspaces.find((w) => w.id === id)
    setDeleteTarget({
      id,
      name: targetWs?.name || "Bu sohbet",
    })
  }

  const confirmDeleteWorkspace = async () => {
    if (!deleteTarget) return
    const id = deleteTarget.id
    setDeleteTarget(null)
    const wasActive = ws.activeWorkspaceId === id || ws.activeWorkspace?.id === id
    await ws.removeWorkspace(id)
    if (wasActive) newChat()
  }

  const handleCitationClick = ({ filename, chunkIndex }) => {
    if (!filename) return
    const targetName = filename.trim().toLowerCase()
    const found = attachments.find((a) => {
      const fn = (a.filename || a.file?.name || "").trim().toLowerCase()
      return fn === targetName || fn.includes(targetName) || targetName.includes(fn)
    })
    if (found) {
      setPreviewAttachment({ ...found, targetChunk: chunkIndex })
    }
  }

  const handleSend = async (rawText) => {
    const q = (rawText || "").trim()
    if (!q || busy) return
    const w = await ws.ensureWorkspace()
    const wid = w.id
    if (window.location.pathname !== `/workspace/${wid}`) {
      window.history.pushState(null, "", `/workspace/${wid}`)
    }
    pushMsg({ id: nid(), role: "user", text: q })
    const qaId = nid()
    pushMsg({ id: qaId, role: "assistant", text: "", streaming: true })
    let acc = ""
    let sources = null
    try {
      await askQAAction(wid, q, {
        onEvent(event, data) {
          if (event === "meta" && data.sources) sources = data.sources
          else if (event === "delta") {
            acc += data.text
            setMsg(qaId, (m) => ({ ...m, text: acc }))
          } else if (event === "done") {
            setMsg(qaId, (m) => ({ ...m, sources: data.sources || sources, streaming: false }))
          } else if (event === "error") {
            setMsg(qaId, (m) => ({ ...m, text: `⚠️ ${data.message}`, streaming: false, sources: m.sources || sources }))
          }
        },
      })
    } catch (err) {
      setMsg(qaId, (m) => ({ ...m, text: `⚠️ Bağlantı hatası: ${err.message}`, streaming: false }))
    }
    ws.hydrate()
  }

  const pushMsg = (m) => setMessages((prev) => [...prev, m])
  const setMsg = (id, fn) => setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)))

  const pickFile = () => {
    if (chatStarted) return
    fileRef.current?.click()
  }

  const acceptFiles = (fileList) => {
    if (chatStarted) return
    const list = [...(fileList || [])]
    if (!list.length) return
    const valid = list.filter((f) => ALLOWED_EXTS.test(f.name))
    if (!valid.length) {
      alert("Yalnızca PDF, TXT veya MD dosyaları yüklenebilir.")
      return
    }
    if (valid.length < list.length) alert("Bazı dosyalar desteklenmiyor ve atlandı. (Yalnızca PDF · TXT · MD)")
    ws.ensureWorkspace().then((w) => {
      if (window.location.pathname !== `/workspace/${w.id}`) {
        window.history.pushState(null, "", `/workspace/${w.id}`)
      }
      startUploads(w.id, valid)
    })
  }

  const onFilePicked = (e) => {
    const input = e.target
    const files = [...(input.files || [])]
    input.value = ""
    if (!files.length) return
    acceptFiles(files)
  }

  const handleDropFiles = (files) => {
    if (!files?.length) return
    acceptFiles(files)
  }

  const startUploads = (wid, files) => {
    const entries = files.map((f) => ({
      key: aid(),
      file: f,
      filename: f.name,
      size: f.size,
      docId: null,
      phase: DocumentStatus.UPLOADING,
      progress: 0,
      error: null,
    }))
    setAttachmentsBoth((prev) => [...prev, ...entries])
    for (const entry of entries) launchOne(wid, entry)
  }

  const launchOne = (wid, entry) => {
    const handle = uploadDocumentXHRAction(wid, entry.file, {
      onProgress: (p) => patchAttach(entry.key, { progress: p }),
      onDone: (res) => {
        uploadHandles.current.delete(handle)
        if (res.status === DocumentStatus.CANCELLED) {
          patchAttach(entry.key, { phase: DocumentStatus.CANCELLED })
          return
        }
        patchAttach(entry.key, { docId: res.id, phase: DocumentStatus.EMBEDDING })
        startStatusPolling(wid)
      },
      onError: (err) => {
        uploadHandles.current.delete(handle)
        patchAttach(entry.key, { phase: DocumentStatus.FAILED, error: err.message })
      },
    })
    uploadHandles.current.add(handle)
  }

  const removeAttachment = (key, docId) => {
    setAttachmentsBoth((prev) => prev.filter((a) => a.key !== key))
    if (docId) deleteDocumentAction(docId).catch(() => {})
  }

  const updCount = attachments.filter((a) => a.phase === DocumentStatus.UPLOADING).length
  const embCount = attachments.filter((a) => a.phase === DocumentStatus.EMBEDDING).length
  let statusText = "belgeler hazırlanıyor…"
  if (updCount && embCount) statusText = `${updCount} dosya yükleniyor · ${embCount} dosya taranıyor`
  else if (updCount) statusText = `${updCount} dosya yükleniyor…`
  else if (embCount) statusText = `${embCount} dosya taranıyor ve indeksleniyor…`
  if (doneCount > 0) statusText = `${doneCount}/${totalCount} işlendi · ${statusText}`

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
          onToggleTheme={() => setTheme((t) => (t === "gemdark" ? "gemlight" : "gemdark"))}
          onBack={inWorkspace ? newChat : undefined}
          title={chatTitle}
        />

        {attachments.length > 0 && (
          <FileBar attachments={attachments} onRemove={removeAttachment} onPreview={setPreviewAttachment} />
        )}

        <main className="ctx-scroll min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 sm:px-6">
            {uploading && messages.length === 0 ? (
              <UploadingState statusText={statusText} />
            ) : messages.length > 0 ? (
              <MessageList messages={messages} onCitationClick={handleCitationClick} />
            ) : allReady ? (
              <ReadyState totalCount={totalCount} />
            ) : (
              <Welcome onPickFile={pickFile} onDropFiles={handleDropFiles} />
            )}
          </div>
        </main>

        {showComposer && (
          <footer className="flex justify-center px-4 pb-4 pt-1 sm:px-6">
            <Composer onSend={handleSend} busy={busy} />
          </footer>
        )}

        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md"
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

        <FilePreviewModal
          attachment={previewAttachment}
          onClose={() => setPreviewAttachment(null)}
        />
      </div>
    </div>
  )
}