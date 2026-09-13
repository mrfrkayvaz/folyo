import { DOC_STATUS_LABELS, SUMMARY_STATUS_LABELS } from "@/constants/labels"
import type { PanelDocument } from "@/types/models"

interface DocumentListProps {
  docs: PanelDocument[] | null
  activeDocId: string | null
  loading: boolean
  onSelect: (id: string) => void
}

export default function DocumentList({ docs, activeDocId, loading, onSelect }: DocumentListProps) {
  return (
    <section className="flex w-80 shrink-0 flex-col border-r border-base-300/40">
      <div className="flex h-14 shrink-0 items-center px-4 text-base font-semibold">
        Dokümanlar
      </div>
      <div className="ctx-scroll min-h-0 flex-1 overflow-y-auto p-2">
        {loading && <span className="loading loading-spinner loading-sm m-3 text-base-content/40" />}
        {!loading && docs?.length === 0 && <p className="p-3 text-xs text-base-content/40">Bu workspace&apos;te doküman yok</p>}
        {!loading &&
          docs?.map((d) => {
            const st = DOC_STATUS_LABELS[d.status] || { label: d.status, cls: "badge-neutral" }
            const ss = d.summary_status ? SUMMARY_STATUS_LABELS[d.summary_status] : null
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => onSelect(d.id)}
                className={`mb-1 w-full rounded-xl border px-3 py-2.5 text-left transition ${
                  activeDocId === d.id
                    ? "border-base-300 bg-base-200/70"
                    : "border-transparent hover:border-base-300 hover:bg-base-200/60"
                }`}
              >
                <p className="truncate text-sm font-medium text-base-content/90">{d.filename}</p>
                <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className={`badge ${st.cls} badge-soft badge-xs`}>{st.label}</span>
                  {ss && <span className={`badge ${ss.cls} badge-soft badge-xs`}>{ss.label}</span>}
                  <span className="text-base-content/45">{d.chunk_count} parça</span>
                </p>
              </button>
            )
          })}
      </div>
    </section>
  )
}