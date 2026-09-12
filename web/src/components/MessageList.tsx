import { useEffect, useRef } from "react"
import UserMessage from "./UserMessage"
import AssistantMessage from "./AssistantMessage"
import { ChatRole } from "../enums/index"
import type { ChatMessageItem, CitationClickTarget } from "../types/chatTypes"

interface MessageListProps {
  messages: ChatMessageItem[]
  onCitationClick: (target: CitationClickTarget) => void
}

export default function MessageList({ messages, onCitationClick }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const prevLast = useRef<string | null>(null)

  // Yalnızca ALT tarafta YENİ mesaj olunca aşağı kaydır (stream güncellemeleri ve
  // üstten prepend sırasında kullanıcıyı sürükleme/yakalama yok).
  useEffect(() => {
    const lastId = messages.length ? messages[messages.length - 1]?.id ?? null : null
    if (lastId && lastId !== prevLast.current) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
    }
    prevLast.current = lastId
  }, [messages])

  return (
    <div className="flex flex-col gap-6 py-8">
      {messages.map((m) =>
        m.role === ChatRole.USER ? (
          <UserMessage key={m.id} m={m} />
        ) : (
          <AssistantMessage key={m.id} m={m} onCitationClick={onCitationClick} />
        ),
      )}
      <div ref={endRef} />
    </div>
  )
}