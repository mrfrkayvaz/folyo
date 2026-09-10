import { DocIcon } from "./icons.jsx"

export default function CitationBadge({ label, filename, pageNumber, chunkIndex, onClick }) {
  const where = pageNumber ? `${pageNumber}. sayfa, ${chunkIndex}. parça` : `${chunkIndex}. parça`
  return (
    <button
      type="button"
      onClick={() => onClick?.({ filename, pageNumber, chunkIndex })}
      className="mx-0.5 inline-flex cursor-pointer items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 font-mono text-xs font-medium text-primary hover:border-primary hover:bg-primary/20 transition align-baseline"
      title={`${filename} — ${where}`}
    >
      <DocIcon className="h-3 w-3 shrink-0" />
      <span>{label}</span>
    </button>
  )
}
