import { describe, expect, it, vi } from "vitest"

describe("apiUrl — boş VITE_API_BASE_URL (aynı-origin)", () => {
  it("önceden / eklemeden aynı-origin path üretir", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "")
    vi.resetModules()
    const { apiUrl } = await import("./apiBase")
    expect(apiUrl("/api/x")).toBe("/api/x")
    expect(apiUrl("api/x")).toBe("/api/x")
    vi.unstubAllEnvs()
  })
})

describe("apiUrl — mutlak API adresi", () => {
  it("sonda slash olsa bile temiz birleştirir", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.folyo.app/")
    vi.resetModules()
    const { apiUrl } = await import("./apiBase")
    expect(apiUrl("/api/x")).toBe("https://api.folyo.app/api/x")
    expect(apiUrl("x")).toBe("https://api.folyo.app/x")
    vi.unstubAllEnvs()
  })

  it("sondaki /api sonekini kırpar (çift /api oluşmaz)", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.folyo.app/api")
    vi.resetModules()
    const { apiUrl } = await import("./apiBase")
    expect(apiUrl("/api/chunks")).toBe("https://api.folyo.app/api/chunks")
    vi.unstubAllEnvs()
  })
})