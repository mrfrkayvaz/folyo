import type { PanelWorkspace } from "@/types/models"

interface WorkspaceListProps {
  workspaces: PanelWorkspace[]
  activeId: string | null
  onSelect: (id: string) => void
}

export default function WorkspaceList({ workspaces, activeId, onSelect }: WorkspaceListProps) {
  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-base-300/40">
      <div className="flex h-14 shrink-0 items-center px-4 text-base font-semibold">
        Sohbetler
      </div>
      <div className="ctx-scroll min-h-0 flex-1 overflow-y-auto p-2">
        {workspaces.length === 0 && <p className="p-3 text-xs text-base-content/40">Henüz sohbet yok</p>}
        {workspaces.map((w) => (
          <button
            key={w.id}
            type="button"
            onClick={() => onSelect(w.id)}
            className={`mb-1 w-full rounded-xl border px-3 py-2.5 text-left transition ${
              activeId === w.id
                ? "border-base-300 bg-base-200/70"
                : "border-transparent hover:border-base-300 hover:bg-base-200/60"
            }`}
          >
            <p className="truncate text-sm font-medium text-base-content/90">{w.name}</p>
            <p className="text-[11px] text-base-content/45">
              {w.doc_count} doküman · {w.message_count} mesaj
            </p>
            {w.summary && <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-base-content/45">{w.summary}</p>}
          </button>
        ))}
      </div>
    </aside>
  )
}