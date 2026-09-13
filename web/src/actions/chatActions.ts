import { apiUrl, httpErrorMessage , authHeaders } from "../lib/http"
import type { QaEventMap, QaEventName, QaEventPayload } from "../types/chatTypes"

async function consumeStream(res: Response, onEvent: (event: QaEventName, data: QaEventPayload) => void) {
  if (!res.ok) throw new Error(await httpErrorMessage(res))
  if (!res.body) throw new Error("Akış desteklenmiyor.")

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ""

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let sep
    while ((sep = buf.indexOf("\n\n")) !== -1) {
      const block = buf.slice(0, sep).replace(/\r/g, "")
      buf = buf.slice(sep + 2)
      if (!block.trim()) continue

      let event: string = "message"
      const dataLines: string[] = []
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim()
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim())
      }

      let payload: unknown = null
      try {
        payload = JSON.parse(dataLines.join("\n"))
      } catch {
        payload = dataLines.join("\n")
      }
      onEvent(event as QaEventName, (payload ?? {}) as QaEventPayload)
    }
  }
}

export interface AskQaOptions {
  onEvent: (event: QaEventName, data: QaEventPayload) => void
}

export async function askQAAction(workspaceId: string, question: string, { onEvent }: AskQaOptions) {
  const res = await fetch(apiUrl(`/api/workspaces/${workspaceId}/qa`), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...authHeaders() },
    body: JSON.stringify({ question }),
  })
  await consumeStream(res, onEvent)
}

export type { QaEventMap }