export interface Workspace {
  id: string
  name: string
  created_at: string
  last_message_at?: string | null
  summary?: string | null
  summary_docs?: string[] | null
}