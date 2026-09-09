import { useEffect, useRef, useState } from "react"
import Header from "./components/Header.jsx"
import Sidebar from "./components/Sidebar.jsx"
import Welcome from "./components/Welcome.jsx"
import MessageList from "./components/MessageList.jsx"
import Composer from "./components/Composer.jsx"
import {
  askQA,
  cancelDocument,
  createWorkspace,
  deleteWorkspace,
  documentStatus,
  getWorkspace,
  listWorkspaces,
  uploadDocumentXHR,
} from "./lib/api.js"

const THEME_KEY = "ctx-theme"
const WS_KEY = "ctx-workspace"
let idCounter = 0
const nid = () => `m${++idCounter}`

const PLACEHOLDER = "Yeni sohbet"

export default function App() {
  const [theme, setTheme] = useState(() => {
    try {
      const q = new URLSearchParams(location.search).get("theme")
      return q || localStorage.getItem(THEME_KEY) || "gemlight"
    } catch {
      return "gemlight"
    }
  })
  const [workspaces, setWorkspaces] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [attach, setAttach] = useState(null) // {file, docId, phase, progress, error}
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const fileRef = useRef(null)
  const uploadRef = useRef(null)
  const pollRef = useRef(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* yoksay */
    }
  }, [theme])

  useEffect(() => {
    return () => {
      clearTimeout(pollRef.current)
      uploadRef.current?.abort()
    }
  }, [])

  const pushMsg = (m) => setMessages((prev) => [...prev, m])
  const setMsg = (id, fn) => setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)))

  // ── workspaces ──────────────────────────────────────────────────────────

  const loadWorkspaces = async () => {
    try {
      const d = await listWorkspaces()
      setWorkspaces(d.workspaces || [])
    } catch {
      /* yoksay */
    }
  }

  useEffect(() => {
    loadWorkspaces()
  }, [])

  const ensureWorkspace = async () => {
    if (activeId) return activeId
    const d = await createWorkspace()
    setWorkspaces((prev) => [d, ...prev])
    setActiveId(d.id)
    try {
      localStorage.setItem(WS_KEY, d.id)
    } catch {}
    return d.id
  }

  const openWorkspace = async (id) => {
    setActiveId(id)
    try {
      localStorage.setItem(WS_KEY, id)
    } catch {}
    setMessages([])
    setSidebarOpen(false)
    try {
      const d = await getWorkspace(id)
      setMessages(
        (d.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          text: m.content,
          sources: m.citations || undefined,
        })),
      )
    } catch {
      /* yoksay */
    }
  }

  // Kaydedilmiş/ilk workspace'i aç
  const openedRef = useRef(false)
  useEffect(() => {
    if (openedRef.current || workspaces.length === 0 || activeId) return
    openedRef.current = true
    let saved = null
    try {
      saved = localStorage.getItem(WS_KEY)
    } catch {}
    openWorkspace(workspaces.find((w) => w.id === saved)?.id || workspaces[0].id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaces])

  const newChat = async () => {
    const d = await createWorkspace()
    setWorkspaces((prev) => [d, ...prev])
    setActiveId(d.id)
    setMessages([])
    try {
      localStorage.setItem(WS_KEY, d.id)
    } catch {}
  }

  const removeWorkspace = async (id) => {
    if (!window.confirm("Bu sohbet ve tüm belgeleri silinsin mi?")) return
    try {
      await deleteWorkspace(id)
    } catch {}
    setWorkspaces((prev) => prev.filter((w) => w.id !== id))
    if (activeId === id) {
      setActiveId(null)
      setMessages([])
      try {
        localStorage.removeItem(WS_KEY)
      } catch {}
    }
  }

  // ── sohbet ──────────────────────────────────────────────────────────────

  const busy = messages.some((m) => m.streaming)

  const handleSend = async (rawText) => {
    const q = (rawText || "").trim()
    if (!q || busy) return
    const wid = await ensureWorkspace()
    pushMsg({ id: nid(), role: "user", text: q })
    const qaId = nid()
    pushMsg({ id: qaId, role: "assistant", text: "", streaming: true })
    let acc = ""
    let sources = null
    try {
      await askQA(wid, q, {
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
    loadWorkspaces()
  }

  // ── belge yükleme (seçer seçmez başlar) ────────────────────────────────

  const pickFile = async () => {
    const wid = await ensureWorkspace()
    if (wid) fileRef.current?.click()
  }

  const onFilePicked = (e) => {
    const f = e.target.files?.[0]
    e.target.value = ""
    if (!f) return
    ensureWorkspace().then((wid) => startUpload(wid, f))
  }

  const startUpload = (wid, file) => {
    uploadRef.current?.abort()
    clearTimeout(pollRef.current)
    setAttach({ file, docId: null, phase: "uploading", progress: 0, error: null })
    const handle = uploadDocumentXHR(wid, file, {
      onProgress: (p) => setAttach((a) => (a ? { ...a, progress: p } : a)),
      onDone: (res) => {
        if (res.status === "cancelled") {
          setAttach((a) => (a ? { ...a, phase: "cancelled" } : a))
          return
        }
        setAttach((a) => (a ? { ...a, docId: res.id, phase: "embedding", progress: 100 } : a))
        pollStatus(res.id)
      },
      onError: (err) => setAttach((a) => (a ? { ...a, phase: "failed", error: err.message } : a)),
    })
    uploadRef.current = handle
  }

  const pollStatus = (docId) => {
    clearTimeout(pollRef.current)
    const tick = async () => {
      try {
        const d = await documentStatus(docId)
        const emb = d.embed || {}
        const prog = emb.chunks ? Math.round(((emb.progress || 0) / emb.chunks) * 100) : null
        if (d.status === "embedded" || emb.status === "completed") {
          setAttach((a) => (a ? { ...a, phase: "embedded", progress: 100 } : a))
          return
        }
        if (d.status === "failed" || emb.status === "failed") {
          setAttach((a) => (a ? { ...a, phase: "failed", error: d.error || "embedding başarısız" } : a))
          return
        }
        if (d.status === "cancelled" || emb.status === "cancelled") {
          setAttach((a) => (a ? { ...a, phase: "cancelled" } : a))
          return
        }
        if (d.status === "pending" || d.status === "embedding") {
          setAttach((a) => (a ? { ...a, phase: "embedding", progress: prog ?? a.progress } : a))
        }
        pollRef.current = setTimeout(tick, 1500)
      } catch {
        pollRef.current = setTimeout(tick, 2000)
      }
    }
    pollRef.current = setTimeout(tick, 400)
  }

  const cancelAttach = () => {
    setAttach((a) => (a ? { ...a, phase: "cancelled" } : a))
    if (attach?.phase === "uploading") uploadRef.current?.abort()
    if (attach?.docId) cancelDocument(attach.docId).catch(() => {})
  }

  const clearAttach = () => {
    clearTimeout(pollRef.current)
    setAttach(null)
  }

  // ── görünüm ─────────────────────────────────────────────────────────────

  const sidebar = (
    <Sidebar
      workspaces={workspaces}
      activeId={activeId}
      onSelect={openWorkspace}
      onNew={newChat}
      onDelete={removeWorkspace}
    />
  )

  return (
    <div className="flex h-dvh flex-col bg-base-100 text-base-content">
      <Header theme={theme} onToggleTheme={toggleTheme} onMenu={() => setSidebarOpen(true)} />

      <div className="flex min-h-0 flex-1">
        <div className="hidden w-72 shrink-0 border-r border-base-300/40 md:block">{sidebar}</div>

        {sidebarOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div className="absolute inset-0 bg-black/40" onClick={() => setSidebarOpen(false)} />
            <div className="absolute inset-y-0 left-0 w-80 bg-base-100 shadow-2xl">{sidebar}</div>
          </div>
        )}

        <main className="ctx-scroll min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 sm:px-6">
            {messages.length === 0 ? (
              <Welcome onPickFile={pickFile} onSuggestion={handleSend} />
            ) : (
              <MessageList messages={messages} />
            )}
          </div>
        </main>
      </div>

      <footer className="px-4 pb-4 pt-1 sm:px-6">
        <Composer
          attach={attach}
          onCancelAttach={cancelAttach}
          onClearAttach={clearAttach}
          onPickFile={pickFile}
          onSend={handleSend}
          busy={busy}
        />
      </footer>

      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
        className="hidden"
        onChange={onFilePicked}
      />
    </div>
  )

  function toggleTheme() {
    setTheme((t) => (t === "gemdark" ? "gemlight" : "gemdark"))
  }
}