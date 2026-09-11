import { useCallback, useEffect, useRef } from "react"
import { getWorkspaceAction } from "../actions/index.js"
import { STATUS_POLL_INTERVAL_MS } from "../constants/index.js"
import { DocumentStatus } from "../enums/index.js"
import { mapDocPhase, terminalPhase } from "../lib/helpers.js"
import { useWorkspacesStore } from "../stores/workspacesStore.js"

/**
 * Workspace durumunu periyodik çeker; yükleme/embed ilerlemesini attaachments'a uygular.
 * `apply` → attachment listesini güncelleyen stable setter.
 * `onWorkspace` → workspace nesnesini store'a işleyen callback.
 * `getAttachments` → güncel attachment listesini veren ref getter (durma koşulu için).
 */
export function useAttachmentPolling({ apply, onWorkspace, getAttachments }) {
  const pollRef = useRef(null)
  const pollWidRef = useRef(null)

  const stop = useCallback(() => {
    clearInterval(pollRef.current)
    pollRef.current = null
    pollWidRef.current = null
  }, [])

  const start = useCallback(
    (wid) => {
      if (pollWidRef.current === wid && pollRef.current) return
      stop()
      pollWidRef.current = wid
      pollRef.current = setInterval(async () => {
        const widNow = pollWidRef.current
        if (!widNow) return
        try {
          const d = await getWorkspaceAction(widNow)
          const docs = new Map((d.documents || []).map((x) => [x.id, x]))
          const wsObj = d.workspace || d
          if (wsObj.id) {
            const store = useWorkspacesStore.getState()
            onWorkspace?.({ ...(store.activeWorkspace || {}), ...wsObj })
          }
          apply((prev) => {
            let changed = false
            const next = prev.map((a) => {
              if (!a.docId) return a
              const doc = docs.get(a.docId)
              if (!doc) return a
              const phase = mapDocPhase(doc.status)
              if (
                phase === a.phase &&
                a.summaryStatus === (doc.summary_status ?? undefined) &&
                a.summary === (doc.summary ?? undefined) &&
                a.starterQuestions === (doc.starter_questions ?? undefined)
              )
                return a
              changed = true
              return {
                ...a,
                phase,
                error: doc.error ?? undefined,
                progress: undefined,
                stats: doc.stats ?? undefined,
                summary: doc.summary ?? undefined,
                summaryStatus: doc.summary_status ?? undefined,
                summaryError: doc.summary_error ?? undefined,
                starterQuestions: doc.starter_questions ?? undefined,
              }
            })
            return changed ? next : prev
          })
          if (getAttachments().every((a) => terminalPhase(a.phase))) {
            const embedded = getAttachments().filter((a) => a.phase === DocumentStatus.EMBEDDED).length
            if (embedded === 0 || wsObj.summary) stop()
          }
        } catch {}
      }, STATUS_POLL_INTERVAL_MS)
    },
    [apply, getAttachments, onWorkspace, stop],
  )

  useEffect(() => () => stop(), [stop])

  return { start, stop }
}