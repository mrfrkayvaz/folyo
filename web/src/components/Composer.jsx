import { useEffect, useRef, useState } from "react"
import { ArrowUpIcon, DocIcon, PlusIcon, XIcon } from "./icons.jsx"
import { formatBytes } from "../lib/api.js"

function attachTip(a) {
  if (a.phase === "uploading") return `dosya yükleniyor %${a.progress}`
  if (a.phase === "embedding") return `embedleniyor %${a.progress}`
  if (a.phase === "embedded") return "✓ embedlendi — soru sorabilirsin"
  if (a.phase === "failed") return `hata: ${a.error || "işlenemedi"}`
  if (a.phase === "cancelled") return "iptal edildi"
  return a.file?.name || ""
}

export default function Composer({ attach, onCancelAttach, onClearAttach, onPickFile, onSend, busy }) {
  const [text, setText] = useState("")
  const taRef = useRef(null)

  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = "auto"
    ta.style.height = Math.min(ta.scrollHeight, 220) + "px"
  }, [text])

  const canSend = !busy && text.trim()
  const submit = () => {
    if (!canSend) return
    onSend(text)
    setText("")
    taRef.current?.focus()
  }

  const terminal = attach && ["embedded", "failed", "cancelled"].includes(attach.phase)

  return (
    <form
      className="mx-auto w-full max-w-3xl"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <div className="flex items-end gap-1 rounded-[26px] border border-base-300 bg-base-200 px-2 py-1.5 shadow-sm transition focus-within:border-primary/50">
        <button
          type="button"
          onClick={onPickFile}
          className="btn btn-circle btn-ghost h-10 w-10 min-h-10 shrink-0 text-base-content/70"
          title="Belge ekle (PDF / TXT / MD / görsel)"
          aria-label="Belge ekle"
        >
          <PlusIcon className="h-5 w-5" />
        </button>

        <div className="flex min-w-0 flex-1 flex-col">
          {attach && (
            <div className="ctx-rise mx-2 mt-1.5 flex w-fit max-w-full items-center gap-1.5 rounded-full bg-base-300/70 py-0.5 pl-1 pr-0.5">
              <span className="tooltip tooltip-top" data-tip={attachTip(attach)}>
                <span className="inline-flex min-w-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium text-base-content/90">
                  <DocIcon className="h-3.5 w-3.5 shrink-0 text-primary" />
                  <span className="max-w-36 truncate sm:max-w-52">{attach.file.name}</span>
                  <span className="flex shrink-0 items-center gap-1">
                    {(attach.phase === "uploading" || attach.phase === "embedding") && (
                      <>
                        <span className="loading loading-spinner loading-xs text-primary" />
                        <span className="text-primary/80">{attach.progress}%</span>
                      </>
                    )}
                    {attach.phase === "embedded" && <span className="text-success">✓ embedlendi</span>}
                    {attach.phase === "failed" && <span className="text-error">hata</span>}
                    {attach.phase === "cancelled" && <span className="text-base-content/50">iptal</span>}
                  </span>
                </span>
              </span>

              <button
                type="button"
                onClick={terminal ? onClearAttach : onCancelAttach}
                className="btn btn-circle btn-ghost h-6 w-6 min-h-6 text-base-content/60 hover:text-base-content"
                title={terminal ? "Kapat" : "İptal"}
                aria-label={terminal ? "Kapat" : "İptal"}
              >
                <XIcon className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          <textarea
            ref={taRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                submit()
              }
            }}
            placeholder={attach ? "Belgeniz yüklenirken soru sorabilirsiniz…" : "Belgeniz hakkında soru sorun…"}
            className="w-full resize-none bg-transparent px-3 py-3 text-[15px] leading-6 text-base-content outline-none placeholder:text-base-content/40"
          />
        </div>

        <button
          type="submit"
          disabled={!canSend}
          className="btn btn-primary btn-circle mb-0.5 h-11 w-11 min-h-11 shrink-0 disabled:border-transparent disabled:bg-base-300 disabled:text-base-content/30"
          aria-label="Gönder"
        >
          <ArrowUpIcon className="h-5 w-5" />
        </button>
      </div>

      <p className="mt-2.5 px-4 text-center text-[11px] leading-4 text-base-content/40">
        Contextus yanıtları yalnızca yüklediğiniz belgelere dayanır; belgede olmayan bilgiyi üretmez.
        Enter gönderir · Shift+Enter yeni satır.
      </p>
    </form>
  )
}