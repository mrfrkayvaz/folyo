import { useEffect, useRef } from "react"
import Avatar from "./Avatar.jsx"
import RichText from "./RichText.jsx"
import { DocIcon, ShieldIcon } from "./icons.jsx"
import { formatBytes } from "../lib/api.js"

function UserMessage({ m }) {
  return (
    <div className="ctx-rise flex justify-end">
      <div className="flex max-w-[88%] flex-col items-end gap-2 sm:max-w-[75%]">
        {m.file && (
          <span className="inline-flex max-w-full items-center gap-2 rounded-full bg-primary/10 py-1 pl-2 pr-3 text-xs text-primary">
            <DocIcon className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{m.file.name}</span>
            <span className="text-primary/60">· {formatBytes(m.file.size)}</span>
          </span>
        )}
        {m.text && (
          <div className="whitespace-pre-wrap rounded-2xl rounded-br-md bg-base-300 px-4 py-2.5 text-[15px] leading-6 text-base-content">
            {m.text}
          </div>
        )}
      </div>
    </div>
  )
}

function AssistantMessage({ m }) {
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
            <RichText text={m.text} />
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
              <span
                key={i}
                className="inline-flex items-center gap-1.5 rounded-full border border-base-300 bg-base-200/70 py-1 pl-2 pr-3 text-xs text-base-content/80"
              >
                <DocIcon className="h-3.5 w-3.5 text-primary" />
                <span className="max-w-52 truncate font-medium">{s.label}</span>
                {s.meta && <span className="text-base-content/45">· {s.meta}</span>}
              </span>
            ))}
            <span className="inline-flex items-center gap-1 text-xs text-success">
              <ShieldIcon className="h-3.5 w-3.5" />
              yalnızca belge kaynaklı
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default function MessageList({ messages }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages])

  return (
    <div className="flex flex-col gap-6 py-8">
      {messages.map((m) =>
        m.role === "user" ? <UserMessage key={m.id} m={m} /> : <AssistantMessage key={m.id} m={m} />,
      )}
      <div ref={endRef} />
    </div>
  )
}