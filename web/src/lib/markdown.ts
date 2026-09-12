/** Minik Markdown ayrıştırıcı: özyinelemeli satır içi + iç içe liste destekli blok.

- Satır içi: `$$...$$` (blok matematik), `$...$` (satır içi matematik), `[Görsel: ...]`,
  atıf `[Belge, sayfa N, parça M]`, `**kalın**`, `` `kod` ``, `*italik*`.
- Kalın/italik İÇİNDE atıf ve matematik özyinelemeyle çözülür (`**[Belge, …, parça N]**`).
- Bloklar: başlık, kod çiti, paragraf, **iç içe** madde/sıralı liste (girinti derinliği).
- Sonuç düğüm ağacıdır; render tarafı (`RichText`) tüketir.
 */

export type InlineNode =
  | { kind: "math"; tex: string; display: boolean }
  | { kind: "image"; path: string }
  | { kind: "citation"; label: string; filename: string; pageNumber: number | null; chunkIndex: number }
  | { kind: "strong"; children: InlineNode[] }
  | { kind: "code"; text: string }
  | { kind: "em"; children: InlineNode[] }
  | { kind: "text"; text: string }

export type ListBlock = { type: "ul" | "ol"; items: ListItem[] }

export interface ListItem {
  text: string
  nested: ListBlock[]
}

export type Block =
  | { type: "code"; lang: string; text: string }
  | { type: "h"; level: number; text: string }
  | { type: "p"; text: string }
  | ListBlock

const MATH_BLOCK_RE = /\$\$([\s\S]+?)\$\$/
const MATH_INLINE_RE = /\$([^\s$][^$\n]*?[^\s$])\$/
const GORSEL_RE = /\[Görsel:\s*([^\]]+?)\s*\]/i
const CITATION_RE = /^\[\s*(.+?)\s*,\s*(?:sayfa\s*(\d+)\s*,\s*)?parça(?:lar)?\s*([^\]]+?)\s*\]$/i

// Satır içi tokenleri (öncelik sırasıyla: matematik → görsel → atıf → kalın → kod → italik).
const INLINE_TOKEN =
  /(\$\$[\s\S]+?\$\$|\$[^\s$][^$\n]*?[^\s$]\$|\[Görsel:[^\]]*\]|\[[^\]]*parça[^\]]*\]|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/gi

// "5,00" gibi döviz/para kalıplarını matematik sanmamak için içerikte matematik izi arar.
const MATH_HINT = /[a-zA-Z\\^_=+\-*/<>≤≥≠π√∑∫±∞∝]/

function isMathText(tex: string): boolean {
  return MATH_HINT.test(tex)
}

export function parseInline(text = ""): InlineNode[] {
  const nodes = text.split(INLINE_TOKEN).filter(Boolean).map((p): InlineNode => {
    if (p.startsWith("$$") && p.endsWith("$$") && p.length > 4) {
      return { kind: "math", tex: p.slice(2, -2).trim(), display: true }
    }
    const inlineMath = p.match(MATH_INLINE_RE)
    if (inlineMath && isMathText(inlineMath[1])) {
      return { kind: "math", tex: inlineMath[1].trim(), display: false }
    }
    const im = p.match(GORSEL_RE)
    if (im) return { kind: "image", path: im[1].trim() }

    const m = p.match(CITATION_RE)
    if (m) {
      // Görünür etiket her zaman "Kaynak: …" — modelin "Belge:"/"Kaynak:" ön ekleri kırpılır.
      const inner = p.slice(1, -1).trim().replace(/^(?:belge|kaynak)\s*:\s*/i, "")
      const filename = m[1].trim().replace(/^(?:belge|kaynak)\s*:\s*/i, "")
      const pageNumber = m[2] ? parseInt(m[2], 10) : null
      const firstNumMatch = m[3].match(/\d+/)
      const chunkIndex = firstNumMatch ? parseInt(firstNumMatch[0], 10) : 1
      return { kind: "citation", label: `Kaynak: ${inner}`, filename, pageNumber, chunkIndex }
    }
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
      return { kind: "strong", children: parseInline(p.slice(2, -2)) }
    if (p.startsWith("`") && p.endsWith("`") && p.length > 2)
      return { kind: "code", text: p.slice(1, -1) }
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
      return { kind: "em", children: parseInline(p.slice(1, -1)) }
    return { kind: "text", text: p }
  })

  // "Kaynak: [X]" / "Belge: [X]" gibi DIŞ ön ekleri kırp (rozet zaten "Kaynak:" ile başlar).
  for (let i = 0; i < nodes.length - 1; i++) {
    const node = nodes[i]
    if (node && node.kind === "text" && nodes[i + 1]?.kind === "citation") {
      nodes[i] = { kind: "text", text: node.text.replace(/\s*(?:belge|kaynak)\s*:\s*$/i, "") }
    }
  }
  return nodes
}

function indentation(ln: string): number {
  const m = ln.match(/^(\s*)/)
  return (m?.[1] ?? "").replace(/\t/g, "  ").length
}

const LIST_MARKER = /^\s*([-*]|\d+\.)\s+(.*)$/

interface ListParseResult {
  list: ListBlock
  next: number
}

function parseList(lines: string[], start: number): ListParseResult {
  const listType: "ol" | "ul" = /^\s*\d+\.\s+/.test(lines[start] ?? "") ? "ol" : "ul"
  const baseDepth = indentation(lines[start])
  const items: ListItem[] = []
  let i = start

  while (i < lines.length) {
    const ln = lines[i]
    if (ln.trim() === "") {
      // Liste içi boş satırları atla (paragrafa bölme).
      i++
      continue
    }
    const m = ln.match(LIST_MARKER)
    if (!m) break
    const dep = indentation(ln)
    if (dep < baseDepth) break
    if (dep === baseDepth) {
      items.push({ text: m[2], nested: [] })
      i++
      continue
    }
    // Daha derin girinti → önceki maddenin iç içe listesi.
    if (!items.length) break
    const sub = parseList(lines, i)
    items[items.length - 1]!.nested.push(sub.list)
    i = sub.next
  }
  return { list: { type: listType, items }, next: i }
}

export function parseBlocks(text: string): Block[] {
  const out: Block[] = []
  const lines = text.split("\n")
  let i = 0

  while (i < lines.length) {
    const ln = lines[i]!

    const fence = ln.match(/^```(\w*)/)
    if (fence) {
      i++
      const code: string[] = []
      while (i < lines.length && !lines[i]!.startsWith("```")) {
        code.push(lines[i]!)
        i++
      }
      i++
      out.push({ type: "code", lang: fence[1] ?? "", text: code.join("\n") })
      continue
    }

    const heading = ln.match(/^(#{1,3})\s+(.*)/)
    if (heading) {
      out.push({ type: "h", level: heading[1]!.length, text: heading[2] ?? "" })
      i++
      continue
    }

    if (LIST_MARKER.test(ln)) {
      const parsed = parseList(lines, i)
      out.push(parsed.list)
      i = parsed.next
      continue
    }

    if (ln.trim() === "") {
      i++
      continue
    }

    const para: string[] = []
    while (
      i < lines.length &&
      lines[i]!.trim() !== "" &&
      !/^```/.test(lines[i]!) &&
      !LIST_MARKER.test(lines[i]!)
    ) {
      para.push(lines[i]!)
      i++
    }
    if (para.length) out.push({ type: "p", text: para.join("\n") })
  }
  return out
}