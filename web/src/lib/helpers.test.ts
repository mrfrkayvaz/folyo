import { beforeEach, describe, expect, it } from "vitest"
import {
  aid,
  mapApiMessage,
  mapDocPhase,
  nid,
  terminalPhase,
} from "./helpers"
import type { ApiMessage } from "../types/chatTypes"

describe("kimlik üreteçleri", () => {
  beforeEach(() => {
    // yardımcı modül sayaçları testler arası sızmamalı — bunları kendi içinde test ediyoruz
  })

  it("nid sıralı ve önekli", () => {
    expect(nid()).toBe("m1")
    expect(nid()).toBe("m2")
  })

  it("aid ayrı sayaç kullanır", () => {
    expect(aid()).toBe("a1")
    expect(aid()).toBe("a2")
  })
})

describe("terminalPhase", () => {
  it("terminal durumlar true", () => {
    for (const s of ["embedded", "failed", "cancelled"]) {
      expect(terminalPhase(s), s).toBe(true)
    }
  })

  it("ara durumlar false", () => {
    for (const s of ["uploading", "pending", "embedding", "bilinmeyen"]) {
      expect(terminalPhase(s), s).toBe(false)
    }
  })
})

describe("mapDocPhase", () => {
  it("backend durumunu gösterim fazına eşler", () => {
    expect(mapDocPhase("uploading")).toBe("uploading")
    expect(mapDocPhase("pending")).toBe("embedding") // sırada → işleniyor
    expect(mapDocPhase("embedding")).toBe("embedding")
    expect(mapDocPhase("embedded")).toBe("embedded")
    expect(mapDocPhase("failed")).toBe("failed")
  })

  it("bilinmeyen değer güvenli şekilde iptal sayılır", () => {
    expect(mapDocPhase("bambaşka")).toBe("cancelled")
  })
})

describe("mapApiMessage", () => {
  const base: ApiMessage = {
    id: "msg-1",
    role: "assistant",
    content: "yanıt metni",
    created_at: "2026-01-01T10:00:00Z",
    citations: null,
  }

  it("citations dizisi formunu sources'a eşler", () => {
    const m = mapApiMessage({
      ...base,
      citations: [{ label: "Kaynak: Rapor.pdf, parça 2", meta: "sayfa 12" }],
    })
    expect(m.id).toBe("msg-1")
    expect(m.role).toBe("assistant")
    expect(m.text).toBe("yanıt metni")
    expect(m.createdAt).toBe("2026-01-01T10:00:00Z")
    expect(m.sources).toHaveLength(1)
    expect(m.sources![0]!.label).toContain("Rapor.pdf")
    expect(m.chunkIds).toBeUndefined()
  })

  it("citations nesne formu tüm alanları taşır", () => {
    const m = mapApiMessage({
      ...base,
      citations: {
        sources: [{ label: "kaynak-a" }],
        chunk_ids: ["c1", "c2"],
        confidence: 0.87,
        confidence_level: "yüksek",
        rejected: false,
        signals: { dense: 0.8, dense_min: 0.45, bm25: 6.2, bm25_min: 1.0 },
      },
    })
    expect(m.sources).toHaveLength(1)
    expect(m.sources![0]!.label).toBe("kaynak-a")
    expect(m.chunkIds).toEqual(["c1", "c2"])
    expect(m.confidence).toBe(0.87)
    expect(m.confidenceLevel).toBe("yüksek")
    expect(m.rejected).toBe(false)
    expect(m.signals).toEqual({ dense: 0.8, dense_min: 0.45, bm25: 6.2, bm25_min: 1.0 })
  })

  it("citation yoksa alanlar tanımsız kalır", () => {
    const m = mapApiMessage(base)
    expect(m.sources).toBeUndefined()
    expect(m.confidence).toBeUndefined()
  })
})