/** Minik Markdown ayrıştırıcı: atıf etiketi + kalın/kod/italik satır içi, bloklar. */

const INLINE_SPLIT =
  /(\[\s*[^\]]*?parça(?:lar)?\b[^\]]*?\]|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[Görsel:[^\]]*\])/gi

const CITATION_RE = /^\[\s*(.+?)\s*,\s*(?:sayfa\s*(\d+)\s*,\s*)?parça(?:lar)?\s*([^\]]+?)\s*\]$/i

const IMAGE_MARKER_RE = /^\[Görsel:\s*([^\]]+?)\s*\]$/i

export function parseInline(text) {
  return text.split(INLINE_SPLIT).filter(Boolean).map((p) => {
    const imageMarker = p.match(IMAGE_MARKER_RE)
    if (imageMarker) return { kind: "image", path: imageMarker[1].trim() }

    const m = p.match(CITATION_RE)
    if (m) {
      const filename = m[1].trim()
      const pageNumber = m[2] ? parseInt(m[2], 10) : null
      const firstNumMatch = m[3].match(/\d+/)
      const chunkIndex = firstNumMatch ? parseInt(firstNumMatch[0], 10) : 1
      return { kind: "citation", label: p.slice(1, -1), filename, pageNumber, chunkIndex }
    }
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4) return { kind: "strong", text: p.slice(2, -2) }
    if (p.startsWith("`") && p.endsWith("`") && p.length > 2) return { kind: "code", text: p.slice(1, -1) }
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2) return { kind: "em", text: p.slice(1, -1) }
    return { kind: "text", text: p }
  })
}

export function parseBlocks(text) {
  const out = []
  const lines = text.split("\n")
  let para = []
  let i = 0

  const flush = () => {
    if (para.length) {
      out.push({ type: "p", text: para.join("\n") })
      para = []
    }
  }

  while (i < lines.length) {
    const ln = lines[i]
    const fence = ln.match(/^```(\w*)/)
    if (fence) {
      flush()
      i++
      const code = []
      while (i < lines.length && !lines[i].startsWith("```")) {
        code.push(lines[i])
        i++
      }
      i++
      out.push({ type: "code", lang: fence[1], text: code.join("\n") })
      continue
    }

    const heading = ln.match(/^#{1,3}\s+(.*)/)
    if (heading) {
      flush()
      out.push({ type: "h", text: heading[1] })
      i++
      continue
    }

    const listMarker = /^\s*([-*]|\d+\.)\s+/
    if (listMarker.test(ln)) {
      flush()
      const ordered = /^\s*\d+\.\s+/.test(ln)
      const items = []
      while (i < lines.length && listMarker.test(lines[i])) {
        items.push(lines[i].replace(listMarker, ""))
        i++
      }
      out.push({ type: ordered ? "ol" : "ul", items })
      continue
    }

    if (ln.trim() === "") {
      flush()
      i++
      continue
    }

    para.push(ln)
    i++
  }
  flush()
  return out
}