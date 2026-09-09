import { useEffect, useRef } from "react"
import UserMessage from "./UserMessage.jsx"
import AssistantMessage from "./AssistantMessage.jsx"
import { ChatRole } from "../enums/chatEnums.js"

export default function MessageList({ messages, onCitationClick }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
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