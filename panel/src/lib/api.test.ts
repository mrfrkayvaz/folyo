import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Gerçek zustand+persist yerine sahte store — localStorage gerektirmez.
const authState: { token: string | null; logout: ReturnType<typeof vi.fn> } = {
  token: null,
  logout: vi.fn(),
}

vi.mock("../store/auth", () => ({
  useAuth: { getState: () => authState },
}))

import { authMe, getDocument, listWorkspaces, login } from "./api"

describe("panel lib/api — jfetch davranışı", () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    authState.token = null
    authState.logout.mockClear()
    fetchMock.mockReset()
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("login: POST /api/auth/login + JSON gövde + Content-Type", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ token: "t", username: "u", user_type: "admin" }), { status: 200 }),
    )
    const res = await login("admin", "sifre")
    expect(res.token).toBe("t")

    const [url, opts] = fetchMock.mock.calls[0]!
    expect(new URL(String(url)).pathname).toBe("/api/auth/login")
    expect(opts.method).toBe("POST")
    expect(opts.headers["Content-Type"]).toBe("application/json")
    expect(JSON.parse(opts.body)).toEqual({ username: "admin", password: "sifre" })
  })

  it("token varsa Authorization başlığı eklenir", async () => {
    authState.token = "tok-p"
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: 1 }), { status: 200 }))
    await authMe()
    const [, opts] = fetchMock.mock.calls[0]!
    expect(opts.headers.Authorization).toBe("Bearer tok-p")
  })

  it("GET isteği gövdesiz gider (Content-Type yok)", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ workspaces: [] }), { status: 200 }))
    await listWorkspaces()
    const [, opts] = fetchMock.mock.calls[0]!
    expect(opts.method ?? "GET").toBe("GET")
    expect(opts.headers["Content-Type"]).toBeUndefined()
  })

  it("401 (login dışı) → logout + oturum hatası", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 401 }))
    await expect(getDocument("d1")).rejects.toThrow("Oturum süresi doldu")
    expect(authState.logout).toHaveBeenCalledOnce()
  })

  it("login yolundaki 401 oturum temizlemez", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"geçersiz kimlik"}', { status: 401 }))
    await expect(login("x", "y")).rejects.toThrow("geçersiz kimlik")
    expect(authState.logout).not.toHaveBeenCalled()
  })

  it("hata gövdesindeki string detail fırlatılır", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"doküman yok"}', { status: 404 }))
    await expect(getDocument("yok")).rejects.toThrow("doküman yok")
  })

  it("JSON dışı hata gövdesinde HTTP durumu kullanılır", async () => {
    fetchMock.mockResolvedValue(new Response("gateway hatası", { status: 502 }))
    await expect(getDocument("x")).rejects.toThrow("HTTP 502")
  })
})