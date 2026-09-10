import { CONTENT_TYPE_LABELS } from "../constants/index.js"

export default function DocumentCard({ attachment: a, onAsk }) {
  const stats = a.stats
  const types = stats?.types ? Object.entries(stats.types) : []

  return (
    <div className="w-full max-w-xl rounded-2xl border border-base-300 bg-base-100 p-4 text-left shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-semibold text-base-content">{a.filename}</span>
        {stats && (
          <span className="shrink-0 text-xs text-base-content/50">
            {stats.pages} sayfa · {stats.chunks} parça
          </span>
        )}
      </div>

      {types.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {types.map(([t, n]) => (
            <span
              key={t}
              className="rounded-full border border-base-300 bg-base-200/70 px-2 py-0.5 text-[11px] text-base-content/70"
            >
              {CONTENT_TYPE_LABELS[t] ?? t} × {n}
            </span>
          ))}
        </div>
      )}

      {a.summary ? (
        <p className="mt-3 text-sm leading-6 text-base-content/80">{a.summary}</p>
      ) : (
        <p className="mt-3 flex items-center gap-2 text-xs text-base-content/40">
          <span className="loading loading-spinner loading-xs text-primary" />
          Özet hazırlanıyor…
        </p>
      )}

      {a.starterQuestions?.length > 0 && (
        <div className="mt-3 flex flex-col gap-1.5">
          {a.starterQuestions.map((q, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onAsk?.(q)}
              className="text-left text-sm text-primary hover:underline"
            >
              <span className="font-mono text-xs text-base-content/40">{i + 1}.</span> {q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}