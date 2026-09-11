import CitationBadge from "./CitationBadge.jsx"
import CodeBlock from "./CodeBlock.jsx"
import { parseBlocks, parseInline } from "../lib/markdown.js"

function inline(text, onCitationClick) {
  return parseInline(text).map((p, i) => {
    if (p.kind === "citation")
      return (
        <CitationBadge
          key={i}
          label={p.label}
          filename={p.filename}
          pageNumber={p.pageNumber}
          chunkIndex={p.chunkIndex}
          onClick={onCitationClick}
        />
      )
    if (p.kind === "strong") return <strong key={i}>{p.text}</strong>
    if (p.kind === "code")
      return (
        <code key={i} className="rounded-md bg-base-300 px-1.5 py-0.5 font-mono text-[0.85em]">
          {p.text}
        </code>
      )
    if (p.kind === "em") return <em key={i}>{p.text}</em>
    return p.text
  })
}

export default function RichText({ text, onCitationClick }) {
  const blocks = parseBlocks(text)
  return (
    <div className="space-y-2.5 text-[15px] leading-7 text-base-content/90">
      {blocks.map((b, i) => {
        if (b.type === "p")
          return (
            <p key={i} className="whitespace-pre-wrap">
              {inline(b.text, onCitationClick)}
            </p>
          )
        if (b.type === "h")
          return (
            <p key={i} className="pt-1 text-[16px] font-semibold leading-7 text-base-content">
              {inline(b.text, onCitationClick)}
            </p>
          )
        if (b.type === "ul")
          return (
            <ul key={i} className="list-disc space-y-1.5 ps-5">
              {b.items.map((it, j) => (
                <li key={j}>{inline(it, onCitationClick)}</li>
              ))}
            </ul>
          )
        if (b.type === "ol")
          return (
            <ol key={i} className="list-decimal space-y-1.5 ps-5">
              {b.items.map((it, j) => (
                <li key={j}>{inline(it, onCitationClick)}</li>
              ))}
            </ol>
          )
        if (b.type === "code") return <CodeBlock key={i} text={b.text} lang={b.lang} />
        return null
      })}
    </div>
  )
}