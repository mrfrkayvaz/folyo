import { useCallback, useEffect, useRef, useState } from "react"
import { askQAAction, olderMessagesAction } from "../actions/index.js"
import { SSE_EVENTS } from "../constants/index.js"
import { mapApiMessage, nid } from "../lib/helpers.js"
import { useWorkspacesStore } from "../stores/workspacesStore.js"

export function useChatMessages() {
  const [messages, setMessages] = useState([])
  const [olderAvailable, setOlderAvailable] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const messagesRef = useRef([])
  const loadingRef = useRef(false)

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const pushMsg = useCallback((m) => setMessages((prev) => [...prev, m]), [])
  const setMsg = useCallback(
    (id, fn) => setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m))),
    [],
  )

  const reset = useCallback(() => {
    setMessages([])
    setOlderAvailable(false)
    setLoadingOlder(false)
    loadingRef.current = false
  }, [])

  const setFromApi = useCallback((apiMessages = [], hasMore = false) => {
    setMessages(apiMessages.map(mapApiMessage))
    setOlderAvailable(Boolean(hasMore))
    setLoadingOlder(false)
    loadingRef.current = false
  }, [])

  const loadOlder = useCallback(async (workspaceId) => {
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
    async (rawText) => {
      const q = (rawText || "").trim()
      if (!q) return

      const store = useWorkspacesStore.getState()
      const w = await store.ensureWorkspace()
      const wid = w.id
      if (window.location.pathname !== `/workspace/${wid}`) {
        window.history.pushState(null, "", `/workspace/${wid}`)
      }

      pushMsg({ id: nid(), role: "user", text: q })
      const qaId = nid()
      pushMsg({ id: qaId, role: "assistant", text: "", streaming: true })

      let acc = ""
      let sources = null
      let metaRejected = false
      let metaConfidence = null
      let metaLevel = null
      let metaChunkIds = null
      let metaSignals = null

      try {
        await askQAAction(wid, q, {
          onEvent(event, data) {
            if (event === SSE_EVENTS.META) {
              if (data.sources) sources = data.sources
              metaRejected = data.rejected === true
              metaConfidence = data.confidence ?? metaConfidence
              metaLevel = data.confidence_level ?? metaLevel
              metaChunkIds = data.chunk_ids ?? metaChunkIds
              metaSignals = data.signals ?? metaSignals
            } else if (event === SSE_EVENTS.DELTA) {
              acc += data.text
              setMsg(qaId, (m) => ({ ...m, text: acc }))
            } else if (event === SSE_EVENTS.DONE) {
              setMsg(qaId, (m) => ({
                ...m,
                sources: data.sources || sources,
                streaming: false,
                confidence: data.confidence ?? metaConfidence,
                confidenceLevel: data.confidence_level ?? metaLevel,
                chunkIds: data.chunk_ids ?? metaChunkIds,
                signals: data.signals ?? metaSignals,
              }))
            } else if (event === SSE_EVENTS.ERROR) {
              setMsg(qaId, (m) => ({
                ...m,
                text: `⚠️ ${data.message}`,
                streaming: false,
                sources: m.sources || sources,
                rejected: metaRejected,
                confidence: metaConfidence,
                confidenceLevel: metaLevel,
                chunkIds: metaChunkIds,
                signals: metaSignals,
              }))
            }
          },
        })
      } catch (err) {
        setMsg(qaId, (m) => ({ ...m, text: `⚠️ Bağlantı hatası: ${err.message}`, streaming: false }))
      }
      useWorkspacesStore.getState().hydrate()
    },
    [pushMsg, setMsg],
  )

  const busy = messages.some((m) => m.streaming)
  const chatStarted = messages.length > 0

  return { messages, busy, chatStarted, reset, setFromApi, ask, olderAvailable, loadingOlder, loadOlder }
}