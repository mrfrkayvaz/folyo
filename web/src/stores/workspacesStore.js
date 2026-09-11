import { create } from "zustand"
import {
  createWorkspaceAction,
  deleteWorkspaceAction,
  listWorkspacesAction,
} from "../actions/index.js"

function getInitialWorkspaceId() {
  if (typeof window === "undefined") return null
  const m = window.location.pathname.match(/^\/workspace\/([^/]+)/)
  return m ? m[1] : null
}

export const useWorkspacesStore = create((set, get) => ({
  workspaces: [],
  activeWorkspaceId: getInitialWorkspaceId(),
  activeWorkspace: null,
  hydrated: false,

  hydrate: async () => {
    try {
      const d = await listWorkspacesAction()
      const ws = d.workspaces || []
      set((s) => {
        const targetId = s.activeWorkspaceId || getInitialWorkspaceId()
        const found = targetId ? ws.find((w) => w.id === targetId) : null
        const active = targetId ? { ...(found || { id: targetId }), ...(s.activeWorkspace || {}) } : null
        return {
          workspaces: ws,
          activeWorkspaceId: targetId,
          activeWorkspace: active,
          hydrated: true,
        }
      })
    } catch {
      set({ hydrated: true })
    }
  },

  goHome: () => set({ activeWorkspaceId: null, activeWorkspace: null }),

  ensureWorkspace: async () => {
    const { activeWorkspace, activeWorkspaceId } = get()
    if (activeWorkspace) return activeWorkspace
    if (activeWorkspaceId) {
      const found = get().workspaces.find((w) => w.id === activeWorkspaceId)
      if (found) return found
    }
    const ws = await createWorkspaceAction()
    set((s) => ({
      workspaces: [ws, ...s.workspaces],
      activeWorkspaceId: ws.id,
      activeWorkspace: ws,
    }))
    return ws
  },

  openWorkspace: (wsOrId) =>
    set((s) => {
      const id = typeof wsOrId === "string" ? wsOrId : wsOrId?.id
      const wsObj =
        typeof wsOrId === "string"
          ? s.workspaces.find((w) => w.id === wsOrId) || { id: wsOrId }
          : wsOrId
      const list = id && wsObj?.name ? s.workspaces.map((w) => (w.id === id ? { ...w, ...wsObj } : w)) : s.workspaces
      return {
        workspaces: list,
        activeWorkspaceId: id || null,
        activeWorkspace: wsObj || null,
      }
    }),

  removeWorkspace: async (id) => {
    try {
      await deleteWorkspaceAction(id)
    } catch {}
    set((s) => {
      const isCurrent = s.activeWorkspaceId === id
      return {
        workspaces: s.workspaces.filter((w) => w.id !== id),
        activeWorkspaceId: isCurrent ? null : s.activeWorkspaceId,
        activeWorkspace: isCurrent ? null : s.activeWorkspace,
      }
    })
  },
}))