/**
 * Contextus — web-api istemcisi.
 * Workspace'li yapı: sohbet = workspace, belgeler workspace'e yüklenir,
 * sorgu workspace-scope'lu. Upload XHR ile (client-side progress + iptal).
 */

export function formatBytes(bytes) {
  if (!bytes) return ""
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function consume(res, onEvent) {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* yoksay */
    }
    throw new Error(msg)
  }
  if (!res.body) throw new Error("Akış desteklenmiyor.")

  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ""
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let sep
    while ((sep = buf.indexOf("\n\n")) !== -1) {
      const block = buf.slice(0, sep).replace(/\r/g, "")
      buf = buf.slice(sep + 2)
      if (!block.trim()) continue
      let event = "message"
      const dataLines = []
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim()
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim())
      }
      let payload = null
      try {
        payload = JSON.parse(dataLines.join("\n"))
      } catch {
        payload = dataLines.join("\n")
      }
      onEvent?.(event, payload)
    }
  }
}

async function jfetch(url, opts = {}) {
  const res = await fetch(url, opts)
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* yoksay */
    }
    throw new Error(msg)
  }
  return res.json()
}

// ── Workspaces ───────────────────────────────────────────────────────────────

export const createWorkspace = () => jfetch("/api/workspaces", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
export const listWorkspaces = () => jfetch("/api/workspaces")
export const getWorkspace = (wid) => jfetch(`/api/workspaces/${wid}`)
export const deleteWorkspace = (wid) => jfetch(`/api/workspaces/${wid}`, { method: "DELETE" })

// ── Documents ────────────────────────────────────────────────────────────────

/** XHR tabanlı stream upload — progress + iptal destekler. {promise, abort} döner. */
export function uploadDocumentXHR(workspaceId, file, { onProgress, onDone, onError } = {}) {
  const xhr = new XMLHttpRequest()
  const url = `/api/workspaces/${workspaceId}/documents?size=${file.size}&filename=${encodeURIComponent(file.name)}`
  const promise = new Promise((resolve, reject) => {
    xhr.open("POST", url)
    xhr.setRequestHeader("Content-Type", "application/octet-stream")
    xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name))
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        let data = null
        try {
          data = JSON.parse(xhr.responseText)
        } catch {
          data = { status: "pending" }
        }
        onDone?.(data)
        resolve(data)
      } else {
        const err = new Error(xhr.responseText?.slice(0, 200) || `HTTP ${xhr.status}`)
        onError?.(err)
        reject(err)
      }
    }
    xhr.onerror = () => {
      const err = new Error("Bağlantı hatası — yükleme kesildi.")
      onError?.(err)
      reject(err)
    }
    xhr.send(file)
  })
  return { promise, abort: () => xhr.abort() }
}

export const documentStatus = (did) => jfetch(`/api/documents/${did}`)
export const cancelDocument = (did) => jfetch(`/api/documents/${did}/cancel`, { method: "POST" })
export const deleteDocument = (did) => jfetch(`/api/documents/${did}`, { method: "DELETE" })

// ── QA (SSE) ─────────────────────────────────────────────────────────────────

export async function askQA(workspaceId, question, { onEvent } = {}) {
  const res = await fetch(`/api/workspaces/${workspaceId}/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ question }),
  })
  await consume(res, onEvent)
}