import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("../store/auth", () => ({
  useAuth: { getState: () => ({ token: null, logout: vi.fn() }) },
}))

import {
  chunksAction,
  createWorkspaceAction,
  deleteWorkspaceAction,
  listWorkspacesAction,
  olderMessagesAction,
} from "./workspaceActions"

describe("workspace action'ları — URL ve istek şekli", () => {
  // Gerçek dev ortamında VITE_API_BASE_URL=http://localhost:8000 (.env) → URL'ler
  // mutlak gelir; onaylar pathname + sorgu parametreleri üzerinden yapılır (taban değişimine dayanıklı).
  const fetchMock = vi.fn()

  function pathOf(call: unknown[]): string {
    return new URL(String(call[0])).pathname
  }

  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ workspaces: [] }), { status: 200 }))
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("liste GET /api/workspaces", async () => {
    await listWorkspacesAction()
    expect(pathOf(fetchMock.mock.calls[0]!)).toBe("/api/workspaces")
  })

  it("oluşturma POST + JSON gövdesi", async () => {
    await createWorkspaceAction()
    const [url, opts] = fetchMock.mock.calls[0]!
    expect(pathOf(fetchMock.mock.calls[0]!)).toBe("/api/workspaces")
    expect(opts.method).toBe("POST")
    expect(opts.headers["Content-Type"]).toBe("application/json")
    expect(opts.body).toBe("{}")
  })

  it("silme DELETE doğru path", async () => {
    await deleteWorkspaceAction("ws-3")
    const [, opts] = fetchMock.mock.calls[0]!
    expect(pathOf(fetchMock.mock.calls[0]!)).toBe("/api/workspaces/ws-3")
    expect(opts.method).toBe("DELETE")
  })

  it("eski mesajlar: before_at/before_id/limit parametreleri", async () => {
    await olderMessagesAction("ws-3", { beforeAt: "2026-01-01T00:00:00Z", beforeId: "m-9", limit: 25 })
    const u = new URL(String(fetchMock.mock.calls[0]![0]))
    expect(u.pathname).toBe("/api/workspaces/ws-3/messages")
    expect(u.searchParams.get("limit")).toBe("25")
    expect(u.searchParams.get("before_at")).toBe("2026-01-01T00:00:00Z")
    expect(u.searchParams.get("before_id")).toBe("m-9")
  })

  it("eski mesajlar: atlanan parametreler URL'e girmez", async () => {
    await olderMessagesAction("ws-3", { beforeAt: "", beforeId: "" })
    const u = new URL(String(fetchMock.mock.calls[0]![0]))
    expect(u.pathname).toBe("/api/workspaces/ws-3/messages")
    expect(u.searchParams.get("limit")).toBe("10")
    expect(u.searchParams.has("before_at")).toBe(false)
    expect(u.searchParams.has("before_id")).toBe(false)
  })

  it("chunk sorgusu ids virgülle birleştirir", async () => {
    await chunksAction(["c1", "c2", "c3"])
    const u = new URL(String(fetchMock.mock.calls[0]![0]))
    expect(u.pathname).toBe("/api/chunks")
    expect(u.searchParams.get("ids")).toBe("c1,c2,c3")
  })
})