import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("../store/auth", () => ({
  useAuth: { getState: () => ({ token: "tok", logout: vi.fn() }) },
}))

import { askQAAction } from "./chatActions"
import type { QaEventName, QaEventPayload } from "../types/chatTypes"

describe("askQAAction — SSE akışı", () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal("fetch", fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function sseResponse(body: string, status = 200): Response {
    return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } })
  }

  it("event/data bloklarını çözüp onEvent'e iletir", async () => {
    const body = [
      'event: delta',
      'data: {"t":"bir"}',
      "",
      'event: delta',
      'data: {"t":"iki"}',
      "",
      'event: done',
      'data: {}',
      "",
    ].join("\n")
    fetchMock.mockResolvedValue(sseResponse(body))

    const events: Array<[QaEventName, QaEventPayload]> = []
    await askQAAction("ws-1", "soru", { onEvent: (e, d) => events.push([e, d]) })

    const [url, opts] = fetchMock.mock.calls[0]!
    expect(url).toMatch(/\/api\/workspaces\/ws-1\/qa$/)
    expect(opts.headers.Accept).toBe("text/event-stream")
    expect(opts.body).toBe('{"question":"soru"}')

    expect(events).toEqual([
      ["delta", { t: "bir" }],
      ["delta", { t: "iki" }],
      ["done", {}],
    ])
  })

  it("JSON dışı data ham string olarak iletilir", async () => {
    const body = "data: ham metin\n\n"
    fetchMock.mockResolvedValue(sseResponse(body))

    const events: Array<[QaEventName, QaEventPayload]> = []
    await askQAAction("ws-1", "s", { onEvent: (e, d) => events.push([e, d]) })

    expect(events).toEqual([["message", "ham metin"]])
  })

  it("çok satırlı data birleştirilir (pretty JSON)", async () => {
    const body = 'data: {\ndata: "key": "value"\ndata: }\n\n'
    fetchMock.mockResolvedValue(sseResponse(body))

    const events: Array<[QaEventName, QaEventPayload]> = []
    await askQAAction("ws-1", "s", { onEvent: (e, d) => events.push([e, d]) })
    expect(events[0]![0]).toBe("message")
    expect(events[0]![1]).toEqual({ key: "value" })
  })

  it("event etiketli tek satır data", async () => {
    fetchMock.mockResolvedValue(sseResponse('event: meta\ndata: {"done":false}\n\n'))
    const events: Array<[QaEventName, QaEventPayload]> = []
    await askQAAction("ws-1", "s", { onEvent: (e, d) => events.push([e, d]) })
    expect(events[0]![0]).toBe("meta")
    expect(events[0]![1]).toEqual({ done: false })
  })

  it("HTTP hatası httpErrorMessage ile fırlatılır", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"kota aşıldı"}', { status: 429 }))
    await expect(askQAAction("ws-1", "s", { onEvent: vi.fn() })).rejects.toThrow("kota aşıldı")
  })

  it("gövde yoksa akış desteklenmiyor hatası", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 200 }))
    await expect(askQAAction("ws-1", "s", { onEvent: vi.fn() })).rejects.toThrow(
      "Akış desteklenmiyor",
    )
  })
})