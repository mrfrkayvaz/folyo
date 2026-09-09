async function jfetch(url, opts = {}) {
  const res = await fetch(url, opts)
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export function uploadDocumentXHRAction(workspaceId, file, { onProgress, onDone, onError } = {}) {
  const xhr = new XMLHttpRequest()
  const url = `/api/workspaces/${workspaceId}/documents?size=${file.size}&filename=${encodeURIComponent(file.name)}`

  const promise = new Promise((resolve, reject) => {
    xhr.open("POST", url)
    xhr.setRequestHeader("Content-Type", "application/octet-stream")
    xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name))

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress?.(Math.round((e.loaded / e.total) * 100))
      }
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

export const getDocumentStatusAction = (documentId) => jfetch(`/api/documents/${documentId}`)

export const cancelDocumentAction = (documentId) =>
  jfetch(`/api/documents/${documentId}/cancel`, { method: "POST" })

export const deleteDocumentAction = (documentId) =>
  jfetch(`/api/documents/${documentId}`, { method: "DELETE" })

export const getDocumentFileUrlAction = (documentId) => `/api/documents/${documentId}/file`
