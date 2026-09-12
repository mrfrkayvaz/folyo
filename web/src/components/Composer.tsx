import { type ChangeEvent, type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react"
import { ArrowUpIcon } from "./icons"

interface ComposerProps {
  onSend: (text: string) => void
  busy: boolean
}

export default function Composer({ onSend, busy }: ComposerProps) {
  const [text, setText] = useState("")
  const taRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = "auto"
    ta.style.height = Math.min(ta.scrollHeight, 220) + "px"
  }, [text])

  useEffect(() => {
    if (!busy) {
      taRef.current?.focus()
    }
  }, [busy])

  const canSend = !busy && text.trim().length > 0
  const submit = () => {
    if (!canSend) return
    onSend(text)
    setText("")
    taRef.current?.focus()
  }

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    submit()
  }

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => setText(e.target.value)

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form className="mx-auto w-full max-w-3xl" onSubmit={handleSubmit}>
      <div className="flex items-center gap-1 rounded-full border border-base-300 bg-base-200 p-1.5 transition focus-within:border-primary/50">
        <textarea
          ref={taRef}
          rows={1}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Belgeler hakkında soru sorun…"
          className="h-9 w-full resize-none bg-transparent px-3 py-1.5 text-[15px] leading-6 text-base-content outline-none placeholder:text-base-content/40"
        />

        <button
          type="submit"
          disabled={!canSend}
          className="btn btn-primary btn-circle h-9 w-9 min-h-9 shrink-0 disabled:border-transparent disabled:bg-base-300 disabled:text-base-content/30"
          aria-label="Gönder"
        >
          <ArrowUpIcon className="h-5 w-5" />
        </button>
      </div>
    </form>
  )
}