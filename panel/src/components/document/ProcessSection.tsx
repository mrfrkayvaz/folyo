import { DOC_STATUS_LABELS } from "@/constants/labels"
import { SummaryStatus } from "@/constants/enums"
import { formatTs } from "@/utils/formatters"
import type { JobInfo, PanelDocument } from "@/types/models"

interface ProcessSectionProps {
  d: PanelDocument
  job?: JobInfo | null
}

export default function ProcessSection({ d, job }: ProcessSectionProps) {
  const st = DOC_STATUS_LABELS[d.status] || { label: d.status, cls: "badge-neutral" }
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-base-content/50">Süreç</h3>
      <div className="mt-2 rounded-xl border border-base-300 bg-base-100 p-4">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="text-xs text-base-content/60">durum:</span>
          <span className={`badge ${st.cls} badge-soft badge-sm`}>{d.status}</span>
          {job?.status && <span className="text-xs text-base-content/45">job: {job.status}</span>}
          {job?.chunks != null && (
            <progress className="progress progress-primary h-2 w-40" value={job.progress || 0} max={job.chunks} />
          )}
          {job?.chunks != null && (
            <span className="text-xs text-base-content/45">
              {job.progress ?? 0}/{job.chunks}
            </span>
          )}
          {job?.dim && <span className="text-xs text-base-content/45">dim {job.dim}</span>}
        </div>
        {d.error && <p className="mt-2 text-xs text-error">hata: {d.error}</p>}
        {job?.error && <p className="mt-1 text-xs text-error">job hatası: {job.error}</p>}
        {d.summary_status === SummaryStatus.Failed && d.summary_error && (
          <p className="mt-1 text-xs text-error">özet hatası: {d.summary_error}</p>
        )}
        <p className="mt-2 text-xs text-base-content/45">
          {d.created_at && `yüklendi ${formatTs(d.created_at)}`}
          {d.updated_at && ` · güncellendi ${formatTs(d.updated_at)}`}
        </p>
      </div>
    </section>
  )
}