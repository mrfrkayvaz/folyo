import { useMemo } from "react"
import katex from "katex"
import CitationBadge from "./CitationBadge"
import CodeBlock from "./CodeBlock"
import { parseBlocks, parseInline } from "../lib/markdown"
import { apiUrl } from "../lib/apiBase"
import type { Block, InlineNode, ListBlock } from "../lib/markdown"
import type { CitationClickTarget } from "../types/chatTypes"

/** KaTeX ile LaTeX/metin render; hata durumunda ham metni koru (kırma yok). */
function MathView({ tex, display }: { tex: string; display: boolean }) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(tex, {
        throwOnError: false,
        displayMode: display,
        output: "htmlAndMathml",
        strict: false,
      })
    } catch {
      return null
    }
  }, [tex, display])
  if (html === null) {
    return <code className="rounded bg-base-300 px-1 py-0.5 font-mono text-[0.85em]">{tex}</code>
  }
  if (display) {
    return (
      <div
        className="my-2 overflow-x-auto rounded-lg bg-base-200/40 px-3 py-2 text-center [&_.katex]:text-[1.05em]"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    )
  }
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

/** Görsel yer tutucusu `[Görsel: belge_id/dosya_adı]` → kırpım URL'i. */
function imageSrc(path: string): string | null {
  const slash = path.indexOf("/")
  if (slash <= 0 || slash >= path.length - 1) return null
  return apiUrl(`/api/documents/${path.slice(0, slash)}/crops/${path.slice(slash + 1)}`)
}

/** Satır içi düğüm ağacı → React öğeleri (özyinelemeli). */
function inlineNodes(nodes: InlineNode[], onCitationClick: (target: CitationClickTarget) => void) {
  return nodes.map((n, i) => {
    switch (n.kind) {
      case "citation":
        return (
          <CitationBadge
            key={i}
            label={n.label}
            filename={n.filename}
            pageNumber={n.pageNumber}
            chunkIndex={n.chunkIndex}
            onClick={onCitationClick}
          />
        )
      case "image": {
        const src = imageSrc(n.path)
        if (!src)
          return (
            <span key={i} className="font-mono text-xs text-base-content/60">
              {n.path}
            </span>
          )
        return (
          <img
            key={i}
            src={src}
            alt={n.path}
            title={n.path}
            className="my-2 block max-h-96 w-full rounded-xl border border-base-300 object-contain"
          />
        )
      }
      case "math":
        return <MathView key={i} tex={n.tex} display={n.display} />
      case "strong":
        return <strong key={i}>{inlineNodes(n.children, onCitationClick)}</strong>
      case "em":
        return <em key={i}>{inlineNodes(n.children, onCitationClick)}</em>
      case "code":
        return (
          <code key={i} className="rounded-md bg-base-300 px-1.5 py-0.5 font-mono text-[0.85em]">
            {n.text}
          </code>
        )
      default:
        return n.text
    }
  })
}

function renderList(list: ListBlock, onCitationClick: (target: CitationClickTarget) => void) {
  const Tag = list.type === "ol" ? "ol" : "ul"
  const cls = list.type === "ol" ? "list-decimal" : "list-disc"
  return (
    <Tag className={`space-y-1.5 ps-5 ${cls}`}>
      {list.items.map((it, j) => (
        <li key={j}>
          {inlineNodes(parseInline(it.text), onCitationClick)}
          {it.nested.length > 0 && (
            <div className="mt-1.5">
              {it.nested.map((n, k) => (
                <div key={k}>{renderList(n, onCitationClick)}</div>
              ))}
            </div>
          )}
        </li>
      ))}
    </Tag>
  )
}

interface RichTextProps {
  text: string
  onCitationClick: (target: CitationClickTarget) => void
}

export default function RichText({ text, onCitationClick }: RichTextProps) {
  const blocks = parseBlocks(text)
  return (
    <div className="space-y-2.5 text-[15px] leading-7 text-base-content/90">
      {blocks.map((b, i) => {
        if (b.type === "p")
          return (
            <p key={i} className="whitespace-pre-wrap">
              {inlineNodes(parseInline(b.text), onCitationClick)}
            </p>
          )
        if (b.type === "h")
          return (
            <p key={i} className="pt-1 text-[16px] font-semibold leading-7 text-base-content">
              {inlineNodes(parseInline(b.text), onCitationClick)}
            </p>
          )
        if (b.type === "ul" || b.type === "ol")
          return (
            <div key={i}>
              {renderList(b, onCitationClick)}
            </div>
          )
        if (b.type === "code") return <CodeBlock key={i} text={b.text} lang={b.lang} />
        return null
      })}
    </div>
  )
}