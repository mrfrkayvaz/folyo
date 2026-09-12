import type { PanelDocument } from "../../types/models"

interface SummarySectionProps {
  d: PanelDocument
}

export default function SummarySection({ d }: SummarySectionProps) {
  let body
  if (d.summary) {
    body = <p className="whitespace-pre-wrap text-sm leading-6 text-base-content/85">{d.summary}</p>
  } else if (d.summary_status === "pending") {
    body = (
      <p className="flex items-center gap-2 text-xs text-base-content/45">
        <span className="loading loading-spinner loading-xs text-primary" />
        Özet hazırlanıyor…
      </p>
    )
  } else if (d.summary_status === "failed") {
    body = <p className="text-xs text-error">Özet oluşturulamadı.</p>
  } else {
    body = <p className="text-xs text-base-content/40">Bu belge için özet yok.</p>
  }

  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-base-content/50">Özet</h3>
      <div className="mt-2 rounded-xl border border-base-300 bg-base-100 p-4">{body}</div>
    </section>
  )
}