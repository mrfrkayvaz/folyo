import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("../store/auth", () => ({
  useAuth: { getState: () => ({ token: "tok", logout: vi.fn() }) },
}))

import {
  cancelDocumentAction,
  deleteDocumentAction,
  getDocumentFileUrlAction,
  getDocumentStatusAction,
  uploadDocumentAction,
} from "./documentActions"

describe("uploadDocumentAction", () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("doğru URL + akış header'ları + body olarak dosyayı gönderir", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: "doc-1", status: "uploading" }), { status: 201 }),
    )
    const file = new File(["pdf içeriği"], "rapor özeti.pdf", { type: "application/pdf" })

    const res = await uploadDocumentAction("ws-9", file)

    expect(res).toEqual({ id: "doc-1", status: "uploading" })
    const [url, opts] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/api/workspaces/ws-9/documents")
    expect(String(url)).toContain(`size=${file.size}`)
    expect(String(url)).toContain(`filename=${encodeURIComponent(file.name)}`)
    expect(opts.method).toBe("POST")
    expect(opts.headers["Content-Type"]).toBe("application/octet-stream")
    expect(opts.headers["X-Filename"]).toBe(encodeURIComponent(file.name))
    expect(opts.headers.Authorization).toBe("Bearer tok")
    expect(opts.body).toBe(file)
  })

  it("hata gövdesi 200 karaktere kırpılır", async () => {
    const longText = "x".repeat(500)
    fetchMock.mockResolvedValue(new Response(longText, { status: 400 }))
    await expect(uploadDocumentAction("ws-9", new File(["a"], "a.txt"))).rejects.toThrow(
      "x".repeat(200),
    )
  })

  it("boş hata gövdesinde durum kodu kullanılır", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 500 }))
    await expect(uploadDocumentAction("ws-9", new File(["a"], "a.txt"))).rejects.toThrow(
      "HTTP 500",
    )
  })
})

describe("diğer document action'ları", () => {
  // Gerçek dev ortamında VITE_API_BASE_URL (.env) mutlak URL üretir — path onayları
  // pathname üzerinden yapılır.
  const fetchMock = vi.fn()

  function pathOf(call: unknown[]): string {
    return new URL(String(call[0])).pathname
  }

  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("durum sorgusu doğru path'e gider", async () => {
    await getDocumentStatusAction("doc-x")
    expect(pathOf(fetchMock.mock.calls[0]!)).toBe("/api/documents/doc-x")
  })

  it("iptal POST", async () => {
    await cancelDocumentAction("doc-x")
    const [, opts] = fetchMock.mock.calls[0]!
    expect(pathOf(fetchMock.mock.calls[0]!)).toBe("/api/documents/doc-x/cancel")
    expect(opts.method).toBe("POST")
  })

  it("silme DELETE", async () => {
    await deleteDocumentAction("doc-x")
    const [, opts] = fetchMock.mock.calls[0]!
    expect(pathOf(fetchMock.mock.calls[0]!)).toBe("/api/documents/doc-x")
    expect(opts.method).toBe("DELETE")
  })

  it("indirme URL'i apiUrl üzerinden", () => {
    expect(getDocumentFileUrlAction("doc-x")).toMatch(/\/api\/documents\/doc-x\/file$/)
  })
})