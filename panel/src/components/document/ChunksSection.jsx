import { CONTENT_TYPE_LABELS, IMAGE_KIND_LABELS } from "../../constants/labels.js"

export default function ChunksSection({ chunks }) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
        Chunk&apos;lar ({chunks.length})
      </h3>
      <div className="mt-2 flex flex-col gap-2">
        {chunks.map((c) => (
          <div key={c.chunk_index} className="rounded-xl border border-base-300 bg-base-100 p-3">
            <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className="font-mono text-base-content/60">#{c.chunk_index}</span>
              <span className="badge badge-warning badge-soft badge-xs">
                {CONTENT_TYPE_LABELS[c.content_type] ?? c.content_type}
              </span>
              {c.image_kind && (
                <span className="text-base-content/45">{IMAGE_KIND_LABELS[c.image_kind] ?? c.image_kind}</span>
              )}
              <span className="text-base-content/45">sayfa {c.page_number}</span>
              {c.image_path && <span className="badge badge-info badge-soft badge-xs">{c.image_path}</span>}
              {c.section_title && <span className="text-base-content/45">· {c.section_title}</span>}
            </div>
            <pre className="ctx-scroll mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-base-content/75">
              {c.text}
            </pre>
          </div>
        ))}
        {chunks.length === 0 && <p className="text-xs text-base-content/40">Chroma&apos;da chunk bulunamadı.</p>}
      </div>
    </section>
  )
}