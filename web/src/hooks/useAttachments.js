import { useCallback, useEffect, useRef, useState } from "react"
import {
  deleteDocumentAction,
  uploadDocumentXHRAction,
} from "../actions/index.js"
import { ALLOWED_EXTENSIONS, PARTIAL_UNSUPPORTED_MSG, UNSUPPORTED_FILES_MSG } from "../constants/index.js"
import { DocumentStatus } from "../enums/index.js"
import { aid, mapDocPhase } from "../lib/helpers.js"
import { useWorkspacesStore } from "../stores/workspacesStore.js"
import { useAttachmentPolling } from "./useAttachmentPolling.js"

export function useAttachments(onWorkspace) {
  const [attachments, setAttachments] = useState([])
  const attachRef = useRef([])
  const handlesRef = useRef(new Set())

  const apply = useCallback((updater) => {
    setAttachments((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater
      attachRef.current = next
      return next
    })
  }, [])

  const patch = useCallback(
    (key, p) => apply((prev) => prev.map((a) => (a.key === key ? { ...a, ...p } : a))),
    [apply],
  )

  const { start: startPolling, stop: stopPolling } = useAttachmentPolling({
    apply,
    onWorkspace,
    getAttachments: () => attachRef.current,
  })

  const launchOne = useCallback(
    (wid, entry) => {
      const handle = uploadDocumentXHRAction(wid, entry.file, {
        onProgress: (p) => patch(entry.key, { progress: p }),
        onDone: (res) => {
          handlesRef.current.delete(handle)
          if (res.status === DocumentStatus.CANCELLED) return patch(entry.key, { phase: DocumentStatus.CANCELLED })
          patch(entry.key, { docId: res.id, phase: DocumentStatus.EMBEDDING })
          startPolling(wid)
        },
        onError: (err) => {
          handlesRef.current.delete(handle)
          patch(entry.key, { phase: DocumentStatus.FAILED, error: err.message })
        },
      })
      handlesRef.current.add(handle)
    },
    [patch, startPolling],
  )

  const startUploads = useCallback(
    (wid, files) => {
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
      apply((prev) => [...prev, ...entries])
      entries.forEach((e) => launchOne(wid, e))
    },
    [apply, launchOne],
  )

  const acceptFiles = useCallback(
    (fileList) => {
      const list = [...(fileList || [])]
      if (!list.length) return
      const valid = list.filter((f) => ALLOWED_EXTENSIONS.test(f.name))
      if (!valid.length) return alert(UNSUPPORTED_FILES_MSG)
      if (valid.length < list.length) alert(PARTIAL_UNSUPPORTED_MSG)
      useWorkspacesStore.getState().ensureWorkspace().then((w) => {
        if (window.location.pathname !== `/workspace/${w.id}`) {
          window.history.pushState(null, "", `/workspace/${w.id}`)
        }
        startUploads(w.id, valid)
      })
    },
    [startUploads],
  )

  const setFromDocuments = useCallback(
    (docs) => {
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
    (key, docId) => {
      apply((prev) => prev.filter((a) => a.key !== key))
      if (docId) deleteDocumentAction(docId).catch(() => {})
    },
    [apply],
  )

  const reset = useCallback(() => {
    stopPolling()
    for (const h of handlesRef.current) h.abort()
    handlesRef.current.clear()
    apply([])
  }, [apply, stopPolling])

  useEffect(
    () => () => {
      for (const h of handlesRef.current) h.abort()
      handlesRef.current.clear()
    },
    [],
  )

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