import { describe, expect, it } from "vitest"
import {
  ContentType,
  DocumentStatus,
  EmbeddingStatus,
  ImageKind,
  SummaryStatus,
  UserType,
} from "./enums"

describe("DocumentStatus — backend değerleriyle birebir", () => {
  it("değerler", () => {
    expect(DocumentStatus.Uploading).toBe("uploading")
    expect(DocumentStatus.Pending).toBe("pending")
    expect(DocumentStatus.Embedding).toBe("embedding")
    expect(DocumentStatus.Embedded).toBe("embedded")
    expect(DocumentStatus.Failed).toBe("failed")
    expect(DocumentStatus.Cancelled).toBe("cancelled")
  })
})

describe("EmbeddingStatus", () => {
  it("değerler backend ile uyumlu", () => {
    expect(Object.values(EmbeddingStatus)).toEqual([
      "pending", "running", "completed", "failed", "cancelled",
    ])
  })
})

describe("SummaryStatus", () => {
  it("değerler", () => {
    expect(SummaryStatus.Pending).toBe("pending")
    expect(SummaryStatus.Done).toBe("done")
    expect(SummaryStatus.Failed).toBe("failed")
  })
})

describe("ContentType", () => {
  it("değerler backend shared.core.enums ile aynı", () => {
    expect(Object.values(ContentType)).toEqual([
      "text", "table", "ocr_text", "image", "code", "equation",
    ])
  })
})

describe("ImageKind", () => {
  it("değerler", () => {
    expect(Object.values(ImageKind)).toEqual([
      "image_caption", "diagram", "form_data", "scanned_page",
    ])
  })
})

describe("UserType", () => {
  it("admin/user", () => {
    expect(UserType.Admin).toBe("admin")
    expect(UserType.User).toBe("user")
  })
})