export const ChatRole = {
  USER: "user",
  ASSISTANT: "assistant",
} as const

export type ChatRoleKey = keyof typeof ChatRole