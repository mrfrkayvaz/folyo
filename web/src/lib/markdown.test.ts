import { describe, expect, it } from "vitest"
import { parseBlocks, parseInline } from "./markdown"

describe("parseInline", () => {
  it("düz metin → text düğümü", () => {
    expect(parseInline("merhaba")).toEqual([{ kind: "text", text: "merhaba" }])
    expect(parseInline("")).toEqual([])
  })

  it("`**kalın**` → strong (iç içe parçalar)", () => {
    const nodes = parseInline("**kalın yazı**")
    expect(nodes[0]).toEqual({
      kind: "strong",
      children: [{ kind: "text", text: "kalın yazı" }],
    })
  })

  it("kalın içinde atıf özyineleme ile çözülür", () => {
    const nodes = parseInline("**[Document, page 2, chunk 3]**")
    const strong = nodes[0]!
    expect(strong.kind).toBe("strong")
    if (strong.kind !== "strong") throw new Error("beklenmedik düğüm")
    expect(strong.children[0]!.kind).toBe("citation")
  })

  it("`kod` → code", () => {
    const nodes = parseInline("şunu yap: `npm run dev`")
    expect(nodes).toContainEqual({ kind: "code", text: "npm run dev" })
  })

  it("*italik* → em", () => {
    const nodes = parseInline("*vurgu*")
    expect(nodes[0]).toEqual({ kind: "em", children: [{ kind: "text", text: "vurgu" }] })
  })

  it("bankacılık `$5,00` matematik sayılmaz", () => {
    const nodes = parseInline("Fiyat: $5,00")
    expect(nodes.every((n) => n.kind !== "math")).toBe(true)
  })

  it("inline matematik ($...$) → math display:false", () => {
    const nodes = parseInline("enerji $E=mc^2$ formülü")
    expect(nodes).toContainEqual({ kind: "math", tex: "E=mc^2", display: false })
  })

  it("blok matematik ($$...$$) → math display:true", () => {
    const nodes = parseInline("$$\\int_0^1 x\\,dx$$")
    expect(nodes[0]).toEqual({ kind: "math", tex: "\\int_0^1 x\\,dx", display: true })
  })

  it("[Image: yol] → image (eski [Görsel:] ile de çalışır)", () => {
    const nodes = parseInline("şekil: [Image: d1/crop.png]")
    expect(nodes).toContainEqual({ kind: "image", path: "d1/crop.png" })
    const nodesTr = parseInline("şekil: [Görsel: d1/crop.png]")
    expect(nodesTr).toContainEqual({ kind: "image", path: "d1/crop.png" })
  })

  it("atıf: (uyumlu söz dizimi) sayfa+parça bilgisi", () => {
    const nodes = parseInline("[Document, page 12, chunk 45]")
    expect(nodes[0]).toEqual({
      kind: "citation",
      label: "Kaynak: Document, page 12, chunk 45",
      filename: "Document",
      pageNumber: 12,
      chunkIndex: 45,
    })
  })

  it("Türkçe atıf biçimi (varsayılan)", () => {
    const nodes = parseInline("[Belge, sayfa 12, parça 45]")
    expect(nodes[0]).toEqual({
      kind: "citation",
      label: "Kaynak: Belge, sayfa 12, parça 45",
      filename: "Belge",
      pageNumber: 12,
      chunkIndex: 45,
    })
  })

  it("atıf: sayfasız → pageNumber null, chunkIndex 1", () => {
    const nodes = parseInline("[Document, chunk 3]")
    expect(nodes[0]).toMatchObject({ kind: "citation", pageNumber: null, chunkIndex: 3 })
    // Türkçe eski biçim de çalışır
    const nodesTr = parseInline("[Belge, parça 3]")
    expect(nodesTr[0]).toMatchObject({ kind: "citation", pageNumber: null, chunkIndex: 3 })
  })

  it("modelin 'Kaynak:' ön eki görünür etiketten kırpılır ve tekrar eklenir", () => {
    const nodes = parseInline("[Kaynak: Rapor.pdf, chunk 2]")
    const cit = nodes[0] as { kind: string; filename: string; label: string }
    expect(cit.kind).toBe("citation")
    expect(cit.filename).toBe("Rapor.pdf")
    expect(cit.label).toBe("Kaynak: Rapor.pdf, chunk 2")
  })

  it("atıftan önceki dış 'Source:' metni kırpılır", () => {
    const nodes = parseInline("Source: [Document, chunk 1] metni")
    expect(nodes[0]).toEqual({ kind: "text", text: "" }) // ön ek tamamen tüketilir
    expect(nodes[1]!.kind).toBe("citation")
    expect(nodes[2]).toEqual({ kind: "text", text: " metni" }) // atıf sonrası korunur
  })
})

describe("parseBlocks", () => {
  it("başlıklar 1-3 seviye", () => {
    const blocks = parseBlocks("# Ana\n## Alt\n### Alt alt")
    expect(blocks).toEqual([
      { type: "h", level: 1, text: "Ana" },
      { type: "h", level: 2, text: "Alt" },
      { type: "h", level: 3, text: "Alt alt" },
    ])
  })

  it("kod çiti dil etiketi ve çok satır içeriği korur", () => {
    const blocks = parseBlocks("```python\nprint(1)\nprint(2)\n```")
    expect(blocks).toEqual([
      { type: "code", lang: "python", text: "print(1)\nprint(2)" },
    ])
  })

  it("dil etiketsiz çit boş dil", () => {
    const blocks = parseBlocks("```\nx\n```")
    expect(blocks[0]).toEqual({ type: "code", lang: "", text: "x" })
  })

  it("paragraf satırları birleştirir", () => {
    const blocks = parseBlocks("ilk satır\nikinci satır")
    expect(blocks).toEqual([{ type: "p", text: "ilk satır\nikinci satır" }])
  })

  it("madde listesi", () => {
    const blocks = parseBlocks("- bir\n- iki\n\nparagraf")
    expect(blocks[0]).toEqual({
      type: "ul",
      items: [{ text: "bir", nested: [] }, { text: "iki", nested: [] }],
    })
    expect(blocks[1]).toEqual({ type: "p", text: "paragraf" })
  })

  it("sıralı liste", () => {
    const blocks = parseBlocks("1. adım\n2. adım")
    expect(blocks[0]!.type).toBe("ol")
    expect((blocks[0] as { items: unknown[] }).items).toHaveLength(2)
  })

  it("girintili iç içe liste", () => {
    const blocks = parseBlocks("- üst\n  - alt1\n  - alt2\n- üst2")
    const ul = blocks[0] as { items: Array<{ text: string; nested: unknown[] }> }
    expect(ul.items).toHaveLength(2)
    expect(ul.items[0]!.nested).toHaveLength(1)
    const nested = ul.items[0]!.nested[0] as { type: string; items: unknown[] }
    expect(nested.type).toBe("ul")
    expect(nested.items).toHaveLength(2)
  })
})