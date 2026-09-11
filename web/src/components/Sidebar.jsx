import { timeAgo } from "../utils/formatters.js"
import { PlusIcon, XIcon } from "./icons.jsx"

export default function Sidebar({ workspaces, activeId, onSelect, onNew, onDelete }) {
  return (
    <aside className="flex w-52 shrink-0 flex-col border-r border-base-300/40 md:w-64">
      <div className="flex items-center gap-2 px-3 pb-2 pt-3">
        <img src="/logo.svg" alt="Folyo" className="h-9 w-9 shrink-0 rounded-lg drop-shadow" />
        <span className="truncate text-lg font-semibold tracking-tight">Folyo</span>
      </div>

      <div className="px-2 pb-3 pt-1">
        <a
          href="/"
          onClick={(e) => {
            if (!e.ctrlKey && !e.metaKey) {
              e.preventDefault()
              onNew()
            }
          }}
          className="btn btn-block gap-2 border-transparent bg-primary/15 text-primary hover:border-transparent hover:bg-primary/25"
        >
          <PlusIcon className="h-4 w-4" />
          Yeni sohbet
        </a>
      </div>

      <div className="ctx-scroll flex-1 space-y-1 overflow-y-auto px-2 pb-4">
        {workspaces.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-base-content/40">Henüz sohbet yok</p>
        )}
        {workspaces.map((w) => (
          <a
            key={w.id}
            href={`/workspace/${w.id}`}
            onClick={(e) => {
              if (!e.ctrlKey && !e.metaKey) {
                e.preventDefault()
                onSelect(w.id)
              }
            }}
            className={`group flex cursor-pointer items-center gap-1 rounded-xl px-2 py-2 transition ${
              w.id === activeId ? "bg-base-200" : "hover:bg-base-200/60"
            }`}
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{w.name}</span>
              <span className="block text-[11px] text-base-content/45">
                {timeAgo(w.last_message_at || w.created_at)}
              </span>
            </span>
            <button
              type="button"
              title="Sohbeti sil"
              className="btn btn-circle btn-ghost btn-xs opacity-0 group-hover:opacity-100"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                onDelete(w.id)
              }}
            >
              <XIcon className="h-3.5 w-3.5" />
            </button>
          </a>
        ))}
      </div>
    </aside>
  )
}