import { useEffect, useRef } from "react"
import UserMessage from "./UserMessage.jsx"
import AssistantMessage from "./AssistantMessage.jsx"
import { ChatRole } from "../enums/chatEnums.js"

export default function MessageList({ messages, onCitationClick }) {
  const endRef = useRef(null)
  const prevLast = useRef(null)

  // Yalnızca ALT tarafta YENİ mesaj olunca aşağı kaydır (stream güncellemeleri ve
  // üstten prepend sırasında kullanıcıyı sürükleme/yakalama yok).
  useEffect(() => {
    const lastId = messages.length ? messages[messages.length - 1].id : null
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