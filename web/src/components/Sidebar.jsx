import { PlusIcon, XIcon } from "./icons.jsx"

function timeAgo(iso) {
  if (!iso) return ""
  const t = new Date(iso).getTime()
  const diff = Math.max(0, Date.now() - t)
  const m = Math.floor(diff / 60000)
  if (m < 1) return "şimdi"
  if (m < 60) return `${m} dk`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} sa`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d} gün`
  return new Date(iso).toLocaleDateString("tr-TR")
}

export default function Sidebar({ workspaces, activeId, onSelect, onNew, onDelete }) {
  return (
    <aside className="flex h-full min-h-0 flex-col">
      <div className="p-3">
        <button type="button" onClick={onNew} className="btn btn-primary btn-block gap-2">
          <PlusIcon className="h-4 w-4" />
          Yeni sohbet
        </button>
      </div>

      <div className="ctx-scroll flex-1 space-y-1 overflow-y-auto px-2 pb-4">
        {workspaces.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-base-content/40">Henüz sohbet yok</p>
        )}
        {workspaces.map((w) => (
          <div
            key={w.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(w.id)}
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
                e.stopPropagation()
                onDelete(w.id)
              }}
            >
              <XIcon className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </aside>
  )
}