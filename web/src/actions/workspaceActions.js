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

export const createWorkspaceAction = () =>
  jfetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  })

export const listWorkspacesAction = () => jfetch("/api/workspaces")

export const getWorkspaceAction = (workspaceId) => jfetch(`/api/workspaces/${workspaceId}`)

export const deleteWorkspaceAction = (workspaceId) =>
  jfetch(`/api/workspaces/${workspaceId}`, { method: "DELETE" })
