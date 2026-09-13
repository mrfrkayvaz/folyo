import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Gerçek zustand+persist (localStorage gerektirir) yerine sahte store kullanılır.
const authState: { token: string | null; logout: ReturnType<typeof vi.fn> } = {
  token: null,
  logout: vi.fn(),
}

vi.mock("../store/auth", () => ({
  useAuth: {
    getState: () => authState,
  },
}))

import { apiUrl, authHeaders, httpErrorMessage, jfetch } from "./http"

describe("authHeaders", () => {
  it("token yoksa boş header", () => {
    authState.token = null
    expect(authHeaders()).toEqual({})
  })

  it("token varsa Bearer başlığı", () => {
    authState.token = "tok-123"
    expect(authHeaders()).toEqual({ Authorization: "Bearer tok-123" })
  })
})

describe("httpErrorMessage", () => {
  it("JSON detail (string) çıkarır", async () => {
    const res = new Response('{"detail":"hata mesajı"}', { status: 400 })
    expect(await httpErrorMessage(res)).toBe("hata mesajı")
  })

  it("JSON detail (dizi) stringify edilir", async () => {
    const res = new Response('{"detail":["a","b"]}', { status: 400 })
    expect(await httpErrorMessage(res)).toBe('["a","b"]')
  })

  it("JSON dışı gövdede durum kodu yeterli", async () => {
    const res = new Response("boom", { status: 500 })
    expect(await httpErrorMessage(res)).toBe("HTTP 500")
  })
})

describe("jfetch", () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    authState.token = "tok"
    authState.logout.mockClear()
    fetchMock.mockReset()
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("başarılı yanıtı JSON olarak döndürür ve auth header ekler", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )
    const data = await jfetch<{ ok: boolean }>("/api/test")
    expect(data).toEqual({ ok: true })
    const [url, opts] = fetchMock.mock.calls[0]!
    expect(url).toBe(apiUrl("/api/test"))
    expect(opts.headers.Authorization).toBe("Bearer tok")
  })

  it("401 (login dışı) → logout + oturum hatası", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 401 }))
    await expect(jfetch("/api/workspaces")).rejects.toThrow("Oturum süresi doldu")
    expect(authState.logout).toHaveBeenCalledOnce()
  })

  it("login yolundaki 401 oturumu temizlemez", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"yanlış şifre"}', { status: 401 }))
    await expect(jfetch("/api/auth/login", { method: "POST" })).rejects.toThrow(
      "yanlış şifre",
    )
    expect(authState.logout).not.toHaveBeenCalled()
  })

  it("hata gövdesindeki detail'i fırlatır", async () => {
    fetchMock.mockResolvedValue(
      new Response('{"detail":"belge bulunamadı"}', { status: 404 }),
    )
    await expect(jfetch("/api/documents/x")).rejects.toThrow("belge bulunamadı")
  })
})