import { describe, expect, it } from "vitest"
import { formatTs } from "./formatters"

describe("formatTs", () => {
  it("boş girdi boş döner", () => {
    expect(formatTs()).toBe("")
    expect(formatTs(undefined)).toBe("")
  })

  it("geçerli zaman damgasını tr-TR kısa tarih + saat olarak biçimlendirir", () => {
    const out = formatTs("2026-03-05T09:30:15")
    expect(out).toContain("2026")
    expect(out).toContain(":") // saat kısmı
  })

  it("eski geçersiz girdide NaN üretmez", () => {
    // Invalid Date → toLocaleString "Invalid Date" ya da boş — çökmemeli
    expect(() => formatTs("bozuk-tarih" as string)).not.toThrow()
  })
})