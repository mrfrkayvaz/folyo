import { useEffect, useRef, useState, type ChangeEvent } from "react"
import { getWorkspaceAction } from "../actions/index"
import { DocumentStatus } from "../enums/index"
import { mapApiMessage, mapDocPhase, terminalPhase } from "../lib/helpers"
import { useAttachments } from "./useAttachments"
import { useChatMessages } from "./useChatMessages"
import { useTheme } from "./useTheme"
import { useWorkspacesStore } from "../stores/workspacesStore"
import type { Attachment } from "../types/attachmentTypes"
import type { Workspace } from "../types/workspaceTypes"

const WS_ROUTE = /^\/workspace\/([^/]+)/

interface OpenWorkspaceOpts {
  pushUrl?: boolean
}

interface ChatOpts {
  pushUrl?: boolean
}

export interface CitationClickTarget {
  filename: string
  pageNumber: number | null
  chunkIndex: number
}

interface DeleteTarget {
  id: string
  name: string
}

/**
 * App yaşam döngüsü + seçimler: route, workspace açma, sohbet, dosya, modal durumu.
 * App yalnızca görünüm iskeletidir; tüm düzenleme bu hook'tadır.
 */
export function useAppState() {
  const { theme, toggle } = useTheme()
  const ws = useWorkspacesStore()
  const chat = useChatMessages()
  const att = useAttachments(
    (w: Workspace) => ws.openWorkspace(w),
  )
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)
  const [previewAttachment, setPreviewAttachment] = useState<Attachment | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const routeMatch = window.location.pathname.match(WS_ROUTE)
  const [routeLoading, setRouteLoading] = useState(Boolean(routeMatch))

  // ----- Yaşam döngüsü: ilk yükleme + tarayıcı geçmişi -----
  useEffect(() => {
    void ws.hydrate()

    const match = window.location.pathname.match(WS_ROUTE)
    if (match) void openWorkspace(match[1], { pushUrl: false })

    const handlePopState = () => {
      const m = window.location.pathname.match(WS_ROUTE)
      if (m) void openWorkspace(m[1], { pushUrl: false })
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
  const newChat = (opts: ChatOpts = {}) => {
    const pushUrl = opts?.pushUrl ?? true
    if (pushUrl && window.location.pathname !== "/") {
      window.history.pushState(null, "", "/")
    }
    att.reset()
    chat.reset()
    ws.goHome()
    setRouteLoading(false)
  }

  const openWorkspace = async (id: string, opts: OpenWorkspaceOpts = {}) => {
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
      ws.openWorkspace(d.workspace ?? (d as unknown as Workspace))
      const docs = d.documents ?? []
      if (docs.length) {
        att.setFromDocuments(docs)
        if (docs.some((doc) => !terminalPhase(mapDocPhase(doc.status)))) att.startPolling(id)
      }
      chat.setFromApi(d.messages?.map(mapApiMessage) ?? [], d.has_more)
    } catch {
      window.history.replaceState(null, "", "/")
      ws.goHome()
    } finally {
      setRouteLoading(false)
    }
  }

  // ----- Seçimler & ek işlemler -----
  const handleSend = (rawText: string) => {
    if (chat.busy) return
    void chat.ask(rawText)
  }

  const handleCitationClick = ({ filename, pageNumber, chunkIndex }: CitationClickTarget) => {
    if (!filename) return
    const targetName = filename.trim().toLowerCase()
    const found = att.attachments.find((a) => {
      const fn = (a.filename || a.file?.name || "").trim().toLowerCase()
      return fn === targetName || fn.includes(targetName) || targetName.includes(fn)
    })
    if (found) setPreviewAttachment({ ...found, targetChunk: chunkIndex, targetPage: pageNumber })
  }

  const promptDeleteWorkspace = (id: string) => {
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

  const onFilePicked = (e: ChangeEvent<HTMLInputElement>) => {
    const input = e.target
    const files = Array.from(input.files ?? [])
    input.value = ""
    if (!files.length || chat.chatStarted) return
    att.acceptFiles(files)
  }

  const handleDropFiles = (files: FileList | File[] | null) => {
    if (!files || Array.from(files).length === 0 || chat.chatStarted) return
    att.acceptFiles(files)
  }

  // ----- Görünüm türevleri -----
  const inWorkspace = Boolean(ws.activeWorkspaceId || ws.activeWorkspace)
  const chatStarted = chat.chatStarted
  // Embed işlemleri (upload + tarama) SURERKEN soru inputu asla gözükmez;
  // hem yeni dosya öncesi hem de sohbet devam ederken güvenli davranır.
  const showComposer = !att.hasFailed && !att.uploading && (att.totalCount > 0 || chatStarted)

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