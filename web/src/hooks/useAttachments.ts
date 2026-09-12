import { useCallback, useEffect, useRef, useState } from "react"
import { deleteDocumentAction, uploadDocumentAction } from "../actions/index"
import {
  ALLOWED_EXTENSIONS,
  PARTIAL_UNSUPPORTED_MSG,
  UNSUPPORTED_FILES_MSG,
} from "../constants/index"
import { DocumentStatus } from "../enums/index"
import { aid, mapDocPhase } from "../lib/helpers"
import { useWorkspacesStore } from "../stores/workspacesStore"
import type { Attachment } from "../types/attachmentTypes"
import type { DocumentItem } from "../types/documentTypes"
import { useAttachmentPolling } from "./useAttachmentPolling"

type AttachmentsUpdater = (prev: Attachment[]) => Attachment[]

export function useAttachments(onWorkspace?: (ws: import("../types/workspaceTypes").Workspace) => void) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const attachRef = useRef<Attachment[]>([])

  const apply = useCallback((updater: AttachmentsUpdater | Attachment[]) => {
    setAttachments((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater
      attachRef.current = next
      return next
    })
  }, [])

  const patch = useCallback(
    (key: string, p: Partial<Attachment>) =>
      apply((prev) => prev.map((a) => (a.key === key ? { ...a, ...p } : a))),
    [apply],
  )

  const { start: startPolling, stop: stopPolling } = useAttachmentPolling({
    apply,
    onWorkspace,
    getAttachments: () => attachRef.current,
  })

  const launchOne = useCallback(
    async (wid: string, entry: Attachment) => {
      if (!entry.file) return
      try {
        const res = await uploadDocumentAction(wid, entry.file)
        if (res.status === DocumentStatus.CANCELLED)
          return patch(entry.key, { phase: DocumentStatus.CANCELLED })
        patch(entry.key, { docId: res.id, phase: DocumentStatus.EMBEDDING })
        startPolling(wid)
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        patch(entry.key, { phase: DocumentStatus.FAILED, error: msg })
      }
    },
    [patch, startPolling],
  )

  const startUploads = useCallback(
    (wid: string, files: File[]) => {
      const entries: Attachment[] = files.map((f) => ({
        key: aid(),
        file: f,
        filename: f.name,
        size: f.size,
        docId: null,
        phase: DocumentStatus.UPLOADING,
        progress: undefined,
        error: undefined,
      }))
      apply((prev) => [...prev, ...entries])
      entries.forEach((e) => void launchOne(wid, e))
    },
    [apply, launchOne],
  )

  const acceptFiles = useCallback(
    (fileList: FileList | File[] | null) => {
      const list = Array.from(fileList ?? [])
      if (!list.length) return
      const valid = list.filter((f) => ALLOWED_EXTENSIONS.test(f.name))
      if (!valid.length) return alert(UNSUPPORTED_FILES_MSG)
      if (valid.length < list.length) alert(PARTIAL_UNSUPPORTED_MSG)
      void useWorkspacesStore.getState().ensureWorkspace().then((w) => {
        if (window.location.pathname !== `/workspace/${w.id}`) {
          window.history.pushState(null, "", `/workspace/${w.id}`)
        }
        startUploads(w.id, valid)
      })
    },
    [startUploads],
  )

  const setFromDocuments = useCallback(
    (docs: DocumentItem[]) => {
      if (!docs?.length) return
      apply(
        docs.map((doc) => ({
          key: aid(),
          docId: doc.id,
          filename: doc.filename,
          size: doc.size,
          phase: mapDocPhase(doc.status),
          error: doc.error ?? undefined,
          stats: doc.stats ?? undefined,
          summary: doc.summary ?? undefined,
          summaryStatus: doc.summary_status ?? undefined,
          summaryError: doc.summary_error ?? undefined,
          starterQuestions: doc.starter_questions ?? undefined,
        })),
      )
    },
    [apply],
  )

  const removeAttachment = useCallback(
    (key: string, docId?: string | null) => {
      apply((prev) => prev.filter((a) => a.key !== key))
      if (docId) deleteDocumentAction(docId).catch(() => {})
    },
    [apply],
  )

  const reset = useCallback(() => {
    stopPolling()
    apply([])
  }, [apply, stopPolling])

  useEffect(() => () => stopPolling(), [stopPolling])

  const uploading = attachments.some(
    (a) => a.phase === DocumentStatus.UPLOADING || a.phase === DocumentStatus.EMBEDDING,
  )
  const hasFailed = attachments.some((a) => a.phase === DocumentStatus.FAILED)
  const doneCount = attachments.filter((a) => a.phase === DocumentStatus.EMBEDDED).length
  const totalCount = attachments.length
  const allReady = totalCount > 0 && doneCount === totalCount

  return {
    attachments,
    uploading,
    hasFailed,
    doneCount,
    totalCount,
    allReady,
    acceptFiles,
    removeAttachment,
    reset,
    setFromDocuments,
    startPolling,
    stopPolling,
  }
}