import { useEffect, useRef, useState } from "react"
import { getWorkspaceAction } from "../actions/index.js"
import { DocumentStatus } from "../enums/index.js"
import { mapDocPhase, terminalPhase } from "../lib/helpers.js"
import { useAttachments } from "./useAttachments.js"
import { useChatMessages } from "./useChatMessages.js"
import { useTheme } from "./useTheme.js"
import { useWorkspacesStore } from "../stores/workspacesStore.js"

const WS_ROUTE = /^\/workspace\/([^/]+)/

/**
 * App yaşam döngüsü + seçimler: route, workspace açma, sohbet, dosya, modal durumu.
 * `App.jsx` yalnızca görünüm iskeletidir; tüm düzenleme bu hook'tadır.
 */
export function useAppState() {
  const { theme, toggle } = useTheme()
  const ws = useWorkspacesStore()
  const chat = useChatMessages()
  const att = useAttachments(ws.openWorkspace)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [previewAttachment, setPreviewAttachment] = useState(null)
  const fileRef = useRef(null)

  const routeMatch = window.location.pathname.match(WS_ROUTE)
  const [routeLoading, setRouteLoading] = useState(Boolean(routeMatch))

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
      chat.setFromApi(d.messages, d.has_more)
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
    if (chat.chatStarted) return
    fileRef.current?.click()
  }

  const onFilePicked = (e) => {
    const input = e.target
    const files = [...(input.files || [])]
    input.value = ""
    if (!files.length || chat.chatStarted) return
    att.acceptFiles(files)
  }

  const handleDropFiles = (files) => {
    if (!files?.length || chat.chatStarted) return
    att.acceptFiles(files)
  }

  // ----- Görünüm türevleri -----
  const inWorkspace = Boolean(ws.activeWorkspaceId || ws.activeWorkspace)
  const chatStarted = chat.chatStarted
  const showComposer = !att.hasFailed && ((att.totalCount > 0 && !att.uploading) || chatStarted)

  const updCount = att.attachments.filter((a) => a.phase === DocumentStatus.UPLOADING).length
  const embCount = att.attachments.filter((a) => a.phase === DocumentStatus.EMBEDDING).length
  let statusText = "belgeler hazırlanıyor…"
  if (updCount && embCount) statusText = `${updCount} dosya yükleniyor · ${embCount} dosya taranıyor`
  else if (updCount) statusText = `${updCount} dosya yükleniyor…`
  else if (embCount) statusText = `${embCount} dosya taranıyor ve indeksleniyor…`
  if (att.doneCount > 0) statusText = `${att.doneCount}/${att.totalCount} işlendi · ${statusText}`

  const chatTitle = ws.activeWorkspace?.name?.trim() || (inWorkspace ? "Yeni sohbet" : "")

  return {
    theme,
    toggle,
    ws,
    att,
    chat,
    routeLoading,
    inWorkspace,
    chatStarted,
    showComposer,
    statusText,
    chatTitle,
    deleteTarget,
    previewAttachment,
    setPreviewAttachment,
    setDeleteTarget,
    fileRef,
    newChat,
    openWorkspace,
    handleSend,
    handleCitationClick,
    promptDeleteWorkspace,
    confirmDeleteWorkspace,
    pickFile,
    onFilePicked,
    handleDropFiles,
  }
}