import { DOC_STATUS_LABELS, SUMMARY_STATUS_LABELS } from "../../constants/labels"
import type { JobInfo, PanelDocument } from "../../types/models"

interface DocumentHeaderProps {
  d: PanelDocument
  job?: JobInfo | null
}

export default function DocumentHeader({ d, job }: DocumentHeaderProps) {
  const st = DOC_STATUS_LABELS[d.status] || { label: d.status, cls: "badge-neutral" }
  return (
    <div className="sticky top-0 z-10 border-b border-base-300/40 bg-base-100 px-5 py-3">
      <p className="truncate text-base font-semibold">{d.filename}</p>
      <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-base-content/50">
        <span className={`badge ${st.cls} badge-soft badge-xs`}>{st.label}</span>
        <span>{d.chunk_count} parça</span>
        {d.summary_status && (
          <span>özet: {SUMMARY_STATUS_LABELS[d.summary_status]?.label ?? d.summary_status}</span>
        )}
        {job?.dim && <span>dim {job.dim}</span>}
        {d.file_type && <span>.{d.file_type}</span>}
      </p>
    </div>
  )
}