import DocumentCard from "./DocumentCard.jsx"
import { ShieldIcon } from "./icons.jsx"
import { DocumentStatus } from "../enums/documentEnums.js"

export default function ReadyState({ totalCount, attachments = [], onAsk }) {
  const docs = attachments.filter((a) => a.phase === DocumentStatus.EMBEDDED && a.docId)

  return (
    <div className="flex flex-1 flex-col items-center gap-6 py-10 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-success/10 text-success">
        <ShieldIcon className="h-7 w-7" />
      </span>
      <div>
        <p className="text-base font-medium text-base-content/80">
          {totalCount} belge işlendi — soru sormaya başlayabilirsin
        </p>
        <p className="mt-1 text-xs text-base-content/40">Yanıtlar ✓ yalnızca bu belgelerin kaynağından üretilir.</p>
      </div>

      {docs.map((a) => (
        <DocumentCard key={a.docId} attachment={a} onAsk={onAsk} />
      ))}
    </div>
  )
}