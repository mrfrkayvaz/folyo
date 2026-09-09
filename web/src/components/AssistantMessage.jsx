import Avatar from "./Avatar.jsx"
import RichText from "./RichText.jsx"
import { DocIcon } from "./icons.jsx"

export default function AssistantMessage({ m, onCitationClick }) {
  const thinking = m.streaming && !m.text

  return (
    <div className="ctx-rise flex gap-3">
      <Avatar size="h-8 w-8 text-xs" />
      <div className="min-w-0 flex-1 space-y-3">
        {thinking ? (
          <div className="flex items-center rounded-2xl bg-base-200 px-4 py-3">
            <span className="loading loading-dots text-base-content/50" />
          </div>
        ) : (
          <>
            <RichText text={m.text} onCitationClick={onCitationClick} />
            {m.streaming && (
              <span className="ml-0.5 inline-block animate-pulse text-primary" aria-hidden="true">
                ▍
              </span>
            )}
          </>
        )}

        {m.sources?.length > 0 && !m.streaming && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {m.sources.map((s, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onCitationClick?.({ filename: s.label })}
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-base-300 bg-base-200/70 py-0.5 pl-2 pr-2.5 text-xs text-base-content/80 hover:border-primary/50 hover:bg-base-200 transition"
                title={`${s.label} belgesini önizle`}
              >
                <DocIcon className="h-3.5 w-3.5 text-primary" />
                <span className="max-w-52 truncate font-medium">{s.label}</span>
                {s.meta && <span className="text-base-content/45">· {s.meta}</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
