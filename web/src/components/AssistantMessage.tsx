import { useEffect, useState } from "react"
import { createPortal } from "react-dom"
import Avatar from "./Avatar"
import RichText from "./RichText"
import InspectModal from "./InspectModal"
import { CONFIDENCE_LEVELS } from "../constants/index"
import { ShieldIcon } from "./icons"
import type { ChatMessageItem, CitationClickTarget } from "../types/chatTypes"

interface AssistantMessageProps {
  m: ChatMessageItem
  onCitationClick: (target: CitationClickTarget) => void
}

export default function AssistantMessage({ m, onCitationClick }: AssistantMessageProps) {
  const [showInspect, setShowInspect] = useState(false)
  const thinking = m.streaming && !m.text
  const confMeta = m.confidenceLevel ? CONFIDENCE_LEVELS[m.confidenceLevel] : undefined
  const inspectable = !m.streaming && (m.confidence != null || (m.chunkIds?.length ?? 0) > 0 || m.rejected)

  return (
    <div className="ctx-rise flex gap-3">
      <Avatar size="h-8 w-8 text-xs" />
      <div className="min-w-0 flex-1 space-y-3">
        {thinking ? (
          <span className="loading loading-dots text-base-content/50" />
        ) : m.rejected ? (
          <div className="flex items-start gap-3 rounded-2xl border border-dashed border-warning/50 bg-warning/5 px-4 py-3">
            <ShieldIcon className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
            <div>
              <p className="text-sm font-medium text-warning">Belgelerde doğrulanabilir bilgi bulunamadı</p>
              <p className="mt-1 text-xs leading-5 text-base-content/70">{m.text.replace(/^[\u26A0\uFE0F\s]*/, "")}</p>
            </div>
          </div>
        ) : (
          <>
            <RichText text={m.text} onCitationClick={onCitationClick} />
            {m.streaming && (
              <span
                className="ml-0.5 inline-block h-4 w-0.5 animate-pulse rounded-sm bg-base-content/50 align-text-bottom"
                aria-hidden="true"
              />
            )}
          </>
        )}

        {inspectable && confMeta && m.confidence != null && (
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowInspect(true)}
              title="İncele"
              className={`badge ${confMeta.cls} badge-soft badge-sm cursor-pointer gap-1 transition hover:brightness-95`}
            >
              {confMeta.label} · %{Math.round(m.confidence)}
            </button>
          </div>
        )}
      </div>

      {showInspect && <InspectModal message={m} onClose={() => setShowInspect(false)} />}
    </div>
  )
}