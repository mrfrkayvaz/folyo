import DocumentCard from "./DocumentCard.jsx"
import { ShieldIcon } from "./icons.jsx"
import { DocumentStatus } from "../enums/documentEnums.js"
import { DEFAULT_CHAT_TITLE } from "../constants/index.js"

export default function ReadyState({ totalCount, attachments = [], onAsk, workspace }) {
  const docs = attachments.filter((a) => a.phase === DocumentStatus.EMBEDDED && a.docId)
  const hasWsTitle = workspace?.name && workspace.name !== DEFAULT_CHAT_TITLE

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

      {docs.length > 0 && (
        <div className="w-full max-w-xl rounded-2xl border border-primary/20 bg-primary/5 p-4 text-left">
          {hasWsTitle && <p className="text-sm font-semibold text-primary">{workspace.name}</p>}
          {workspace?.summary ? (
            <p className="mt-1 text-sm leading-6 text-base-content/80">{workspace.summary}</p>
          ) : (
            <p className="mt-1 flex items-center gap-2 text-xs text-base-content/40">
              <span className="loading loading-spinner loading-xs text-primary" />
              Workspace özeti hazırlanıyor…
            </p>
          )}
        </div>
      )}

      {docs.map((a) => (
        <DocumentCard key={a.docId} attachment={a} onAsk={onAsk} />
      ))}
    </div>
  )
}