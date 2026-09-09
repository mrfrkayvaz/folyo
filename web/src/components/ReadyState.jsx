import { ShieldIcon } from "./icons.jsx"

export default function ReadyState({ totalCount }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-success/10 text-success">
        <ShieldIcon className="h-7 w-7" />
      </span>
      <p className="text-base font-medium text-base-content/80">
        {totalCount} belge hazır — soru sormaya başlayabilirsin
      </p>
      <p className="text-xs text-base-content/40">Yanıtlar ✓ yalnızca bu belgelerin kaynağından üretilir.</p>
    </div>
  )
}
