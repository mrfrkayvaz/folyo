interface CodeBlockProps {
  text: string
  lang?: string
}

export default function CodeBlock({ text, lang }: CodeBlockProps) {
  return (
    <pre className="overflow-x-auto rounded-2xl border border-base-300 bg-base-300/50 p-3.5 font-mono text-[13px] leading-6">
      <code data-lang={lang ?? undefined}>{text}</code>
    </pre>
  )
}