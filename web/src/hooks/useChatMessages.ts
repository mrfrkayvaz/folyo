import { useCallback, useEffect, useRef, useState } from "react"
import { askQAAction, olderMessagesAction } from "../actions/index"
import { SSE_EVENTS } from "../constants/index"
import { mapApiMessage, nid } from "../lib/helpers"
import { useWorkspacesStore } from "../stores/workspacesStore"
import type { ChatMessageItem, QaEventName, QaEventPayload, QaMetaPayload } from "../types/chatTypes"

export function useChatMessages() {
  const [messages, setMessages] = useState<ChatMessageItem[]>([])
  const [olderAvailable, setOlderAvailable] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const messagesRef = useRef<ChatMessageItem[]>([])
  const loadingRef = useRef(false)

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const pushMsg = useCallback((m: ChatMessageItem) => setMessages((prev) => [...prev, m]), [])
  const setMsg = useCallback(
    (id: string, fn: (m: ChatMessageItem) => ChatMessageItem) =>
      setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m))),
    [],
  )

  const reset = useCallback(() => {
    setMessages([])
    setOlderAvailable(false)
    setLoadingOlder(false)
    loadingRef.current = false
  }, [])

  const setFromApi = useCallback((apiMessages: ChatMessageItem[] = [], hasMore = false) => {
    setMessages(apiMessages)
    setOlderAvailable(Boolean(hasMore))
    setLoadingOlder(false)
    loadingRef.current = false
  }, [])

  const loadOlder = useCallback(async (workspaceId?: string) => {
    if (!workspaceId || loadingRef.current) return
    const oldest = messagesRef.current[0]
    if (!oldest) return

    loadingRef.current = true
    setLoadingOlder(true)
    try {
      const data = await olderMessagesAction(workspaceId, {
        beforeAt: oldest.createdAt,
        beforeId: oldest.id,
      })
      const incoming = (data.messages || []).map(mapApiMessage)
      setMessages((prev) => {
        const known = new Set(prev.map((m) => m.id))
        const fresh = incoming.filter((m) => !known.has(m.id))
        return [...fresh, ...prev] // kronolojik: eskiler başa eklenir
      })
      setOlderAvailable(Boolean(data.has_more))
    } catch {
      // Ağ hatası: bir daha otomatik denemesin (sayfa yenilenince tekrar dolar).
      setOlderAvailable(false)
    } finally {
      loadingRef.current = false
      setLoadingOlder(false)
    }
  }, [])

  const ask = useCallback(
    async (rawText: string) => {
      const q = (rawText || "").trim()
      if (!q) return

      const store = useWorkspacesStore.getState()
      const w = await store.ensureWorkspace()
      const wid = w.id
      if (window.location.pathname !== `/workspace/${wid}`) {
        window.history.pushState(null, "", `/workspace/${wid}`)
      }

      pushMsg({ id: nid(), role: "user", text: q, createdAt: new Date().toISOString() })
      const qaId = nid()
      pushMsg({ id: qaId, role: "assistant", text: "", createdAt: new Date().toISOString(), streaming: true })

      let acc = ""
      let meta: QaMetaPayload | null = null

      const onEvent = (event: QaEventName, data: QaEventPayload) => {
        if (event === SSE_EVENTS.META) {
          meta = data as QaMetaPayload
        } else if (event === SSE_EVENTS.DELTA) {
          acc += (data as { text: string }).text
          setMsg(qaId, (m) => ({ ...m, text: acc }))
        } else if (event === SSE_EVENTS.DONE) {
          const d = data as QaMetaPayload
          setMsg(qaId, (m) => ({
            ...m,
            sources: d.sources ?? m.sources,
            streaming: false,
            confidence: d.confidence ?? meta?.confidence,
            confidenceLevel: d.confidence_level ?? meta?.confidence_level,
            chunkIds: d.chunk_ids ?? meta?.chunk_ids,
            signals: d.signals ?? meta?.signals,
          }))
        } else if (event === SSE_EVENTS.ERROR) {
          setMsg(qaId, (m) => ({
            ...m,
            text: `Hata: ${(data as { message: string }).message}`,
            streaming: false,
            rejected: meta?.rejected ?? false,
            confidence: meta?.confidence,
            confidenceLevel: meta?.confidence_level,
            chunkIds: meta?.chunk_ids,
            signals: meta?.signals,
          }))
        }
      }

      try {
        await askQAAction(wid, q, { onEvent })
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setMsg(qaId, (m) => ({ ...m, text: `Bağlantı hatası: ${msg}`, streaming: false }))
      }
      useWorkspacesStore.getState().hydrate()
    },
    [pushMsg, setMsg],
  )

  const busy = messages.some((m) => m.streaming)
  const chatStarted = messages.length > 0

  return { messages, busy, chatStarted, reset, setFromApi, ask, olderAvailable, loadingOlder, loadOlder }
}