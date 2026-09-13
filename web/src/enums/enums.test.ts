import { describe, expect, it } from "vitest"
import { ChatRole, DocumentStatus, Theme } from "./index"

describe("chatEnums", () => {
  it("role değerleri backend sözleşmesiyle birebir", () => {
    expect(ChatRole.USER).toBe("user")
    expect(ChatRole.ASSISTANT).toBe("assistant")
  })

  it("value'lar benzersiz", () => {
    expect(new Set(Object.values(ChatRole)).size).toBe(2)
  })
})

describe("documentEnums", () => {
  it("durum değerleri backend shared.core.enums ile aynı", () => {
    expect(Object.values(DocumentStatus)).toEqual([
      "uploading", "pending", "embedding", "embedded", "failed", "cancelled",
    ])
  })
})

describe("themeEnums", () => {
  it("tema değerleri (daisyUI tema adları)", () => {
    expect(Theme.LIGHT).toBe("gemlight")
    expect(Theme.DARK).toBe("gemdark")
  })
})