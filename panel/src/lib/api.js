async function jfetch(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const listWorkspaces = () => jfetch("/api/workspaces")
export const getWorkspace = (id) => jfetch(`/api/workspaces/${id}`)
export const getDocument = (id) => jfetch(`/api/documents/${id}`)