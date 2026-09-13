import { formatTs } from "@/utils/formatters"
import type { DocumentLogItem } from "@/types/models"

interface LogsSectionProps {
  logs?: DocumentLogItem[]
}

const LEVEL_BADGE: Record<DocumentLogItem["level"], string> = {
  info: "badge-info",
  warning: "badge-warning",
  error: "badge-error",
}

const LEVEL_LABEL: Record<DocumentLogItem["level"], string> = {
  info: "bilgi",
  warning: "uyarı",
  error: "hata",
}

export default function LogsSection({ logs = [] }: LogsSectionProps) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
        İşlem Günlüğü ({logs.length})
      </h3>
      {logs.length === 0 ? (
        <div className="mt-2 rounded-xl border border-base-300 bg-base-100 p-4">
          <p className="text-xs text-base-content/40">
            Bu belge için log kaydı yok. Yükleme/embed/özet süreçleri ilerledikçe burada görünür.
          </p>
        </div>
      ) : (
        <div className="mt-2 flex flex-col gap-1.5">
          {logs.map((l) => (
            <div
              key={l.id}
              className="flex items-start gap-3 rounded-xl border border-base-300 bg-base-100 px-3 py-2"
            >
              <span className={`badge badge-sm mt-0.5 shrink-0 ${LEVEL_BADGE[l.level] ?? "badge-neutral"}`}>
                {LEVEL_LABEL[l.level] ?? l.level}
              </span>
              {l.scope && (
                <span className="badge badge-outline badge-sm mt-0.5 shrink-0 text-base-content/60">
                  {l.scope}
                </span>
              )}
              <div className="min-w-0 flex-1">
                <p className="whitespace-pre-wrap break-words text-sm leading-5 text-base-content/85">
                  {l.message}
                </p>
                {l.created_at && (
                  <p className="mt-0.5 font-mono text-[10px] text-base-content/35">
                    {formatTs(l.created_at)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}