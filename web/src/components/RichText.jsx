/* Markdown-lite renderer — stub/API yanıtlarındaki hafif işaretlemeyi JSX'e çevirir.
   Destek: **kalın**, *italik*, `satır içi kod`, ```kod blokları```, başlıklar, - liste, 1. liste. */

function inline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).filter(Boolean)
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
      return <strong key={i}>{p.slice(2, -2)}</strong>
    if (p.startsWith("`") && p.endsWith("`") && p.length > 2)
      return (
        <code key={i} className="rounded-md bg-base-300 px-1.5 py-0.5 font-mono text-[0.85em]">
          {p.slice(1, -1)}
        </code>
      )
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
      return <em key={i}>{p.slice(1, -1)}</em>
    return p
  })
}

function blocksOf(text) {
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
      i++ // kapanış satırı
      out.push({ type: "code", lang: fence[1], text: code.join("\n") })
      continue
    }
    const h = ln.match(/^#{1,3}\s+(.*)/)
    if (h) {
      flush()
      out.push({ type: "h", text: h[1] })
      i++
      continue
    }
    if (/^\s*[-*]\s+/.test(ln)) {
      flush()
      const items = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""))
        i++
      }
      out.push({ type: "ul", items })
      continue
    }
    if (/^\s*\d+\.\s+/.test(ln)) {
      flush()
      const items = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""))
        i++
      }
      out.push({ type: "ol", items })
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

export default function RichText({ text }) {
  const blocks = blocksOf(text)
  return (
    <div className="space-y-2.5 text-[15px] leading-7 text-base-content/90">
      {blocks.map((b, i) => {
        if (b.type === "p")
          return (
            <p key={i} className="whitespace-pre-wrap">
              {inline(b.text)}
            </p>
          )
        if (b.type === "h")
          return (
            <p key={i} className="pt-1 text-[16px] font-semibold leading-7 text-base-content">
              {inline(b.text)}
            </p>
          )
        if (b.type === "ul")
          return (
            <ul key={i} className="list-disc space-y-1.5 ps-5">
              {b.items.map((it, j) => (
                <li key={j}>{inline(it)}</li>
              ))}
            </ul>
          )
        if (b.type === "ol")
          return (
            <ol key={i} className="list-decimal space-y-1.5 ps-5">
              {b.items.map((it, j) => (
                <li key={j}>{inline(it)}</li>
              ))}
            </ol>
          )
        if (b.type === "code")
          return (
            <pre
              key={i}
              className="overflow-x-auto rounded-2xl border border-base-300 bg-base-300/50 p-3.5 font-mono text-[13px] leading-6"
            >
              <code>{b.text}</code>
            </pre>
          )
        return null
      })}
    </div>
  )
}
