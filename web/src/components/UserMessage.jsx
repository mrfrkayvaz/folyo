import { DocIcon } from "./icons.jsx"
import { formatBytes } from "../utils/formatters.js"

export default function UserMessage({ m }) {
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
