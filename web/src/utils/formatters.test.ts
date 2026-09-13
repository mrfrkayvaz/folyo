import { afterEach, describe, expect, it, vi } from "vitest"
import { formatBytes, timeAgo } from "./formatters"

describe("formatBytes", () => {
  it("boş/değersiz girişler boş döner", () => {
    expect(formatBytes()).toBe("")
    expect(formatBytes(null)).toBe("")
    expect(formatBytes(0)).toBe("")
  })

  it("bayt < 1KB", () => {
    expect(formatBytes(512)).toBe("512 B")
  })

  it("KB gösterimi tek ondalık", () => {
    expect(formatBytes(2048)).toBe("2.0 KB")
    expect(formatBytes(1536)).toBe("1.5 KB")
  })

  it("MB gösterimi", () => {
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB")
    expect(formatBytes(25 * 1024 * 1024)).toBe("25.0 MB")
  })

  it("sınır 1KB (1024) KB'ye geçer", () => {
    expect(formatBytes(1023)).toBe("1023 B")
    expect(formatBytes(1024)).toBe("1.0 KB")
  })
})

describe("timeAgo", () => {
  const NOW = new Date("2026-01-10T12:00:00Z").getTime()

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockNow(): void {
    vi.spyOn(Date, "now").mockReturnValue(NOW)
  }

  it("boş girdi boş döner", () => {
    expect(timeAgo()).toBe("")
    expect(timeAgo(null)).toBe("")
  })

  it("1 dk altı → şimdi", () => {
    mockNow()
    expect(timeAgo(new Date(NOW - 30_000).toISOString())).toBe("şimdi")
  })

  it("dakika gösterimi", () => {
    mockNow()
    expect(timeAgo(new Date(NOW - 5 * 60_000).toISOString())).toBe("5 dk")
  })

  it("saat gösterimi", () => {
    mockNow()
    expect(timeAgo(new Date(NOW - 3 * 3_600_000).toISOString())).toBe("3 sa")
  })

  it("gün gösterimi (< 7 gün)", () => {
    mockNow()
    expect(timeAgo(new Date(NOW - 2 * 86_400_000).toISOString())).toBe("2 gün")
  })

  it("7 gün ve üzeri tr-TR tarih gösterir", () => {
    mockNow()
    const iso = new Date(NOW - 30 * 86_400_000).toISOString()
    expect(timeAgo(iso)).toMatch(/\d{2}\.\d{2}\.\d{4}|\d{1,2}\.\d{1,2}\.\d{4}/)
  })

  it("gelecek zaman 0'a sabitlenir (şimdi)", () => {
    mockNow()
    expect(timeAgo(new Date(NOW + 3_600_000).toISOString())).toBe("şimdi")
  })
})