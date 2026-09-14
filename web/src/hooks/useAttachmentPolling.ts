import { useCallback, useEffect, useRef } from "react"
import { getWorkspaceAction } from "../actions/index"
import { STATUS_POLL_INTERVAL_MS } from "../constants/index"
import { DocumentStatus } from "../enums/index"
import { mapDocPhase, terminalPhase } from "../lib/helpers"
import { useWorkspacesStore } from "../stores/workspacesStore"
import type { Attachment } from "../types/attachmentTypes"
import type { DocumentItem } from "../types/documentTypes"
import type { Workspace } from "../types/workspaceTypes"

interface UseAttachmentPollingParams {
  apply: (updater: (prev: Attachment[]) => Attachment[]) => void
  onWorkspace?: (ws: Workspace) => void
  getAttachments: () => Attachment[]
}

/**
 * Workspace durumunu periyodik çeker; yükleme/embed ilerlemesini attachments'a uygular.
 * `apply` → attachment listesini güncelleyen stable setter.
 * `onWorkspace` → workspace nesnesini store'a işleyen callback.
 * `getAttachments` → güncel attachment listesini veren ref getter (durma koşulu için).
 */
export function useAttachmentPolling({ apply, onWorkspace, getAttachments }: UseAttachmentPollingParams) {
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollWidRef = useRef<string | null>(null)

  const stop = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = null
    pollWidRef.current = null
  }, [])

  // Özet üretimi başarısızlığında sonsuz polling olmasın: tüm belgeler terminalken
  // ve özet bir süre gelmezse otomatik dur (ölü "hazırlanıyor…" yerine kullanıcı refresh alır).
  const MAX_POLL_TICKS = 150 // 2 sn aralık → ~5 dk bekleme tavanı

  const start = useCallback((wid: string) => {
    if (pollWidRef.current === wid && pollRef.current) return
    stop()
    pollWidRef.current = wid
    let ticks = 0
    pollRef.current = setInterval(async () => {
      const widNow = pollWidRef.current
      if (!widNow) return
      ticks++
      try {
          const d = await getWorkspaceAction(widNow)
          const docs = new Map((d.documents ?? []).map((x: DocumentItem) => [x.id, x]))
          const wsObj = d.workspace ?? (d as unknown as Workspace)
          if (wsObj.id) {
            const store = useWorkspacesStore.getState()
            onWorkspace?.({ ...(store.activeWorkspace ?? ({} as Workspace)), ...wsObj })
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
            if (embedded === 0 || wsObj.summary || ticks >= MAX_POLL_TICKS) stop()
          }
        } catch {
          /* ağ hatası: bir sonraki turda tekrar dene */
        }
      }, STATUS_POLL_INTERVAL_MS)
    },
    [apply, getAttachments, onWorkspace, stop],
  )

  useEffect(() => () => stop(), [stop])

  return { start, stop }
}