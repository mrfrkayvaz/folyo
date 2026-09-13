import ChunksSection from "@/components/document/ChunksSection"
import DocumentHeader from "@/components/document/DocumentHeader"
import ProcessSection from "@/components/document/ProcessSection"
import QuestionsSection from "@/components/document/QuestionsSection"
import SummarySection from "@/components/document/SummarySection"
import type { DocumentDetailResponse } from "@/types/models"

interface DocumentDetailProps {
  data: DocumentDetailResponse | null
  loading: boolean
}

export default function DocumentDetail({ data, loading }: DocumentDetailProps) {
  if (loading) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <span className="loading loading-spinner loading-lg text-base-content/20" />
      </main>
    )
  }
  if (!data) {
    return (
      <main className="flex flex-1 items-center justify-center text-sm text-base-content/40">
        Soldan bir doküman seç
      </main>
    )
  }

  const { document: d, chunks } = data
  const job = d.process?.job ?? undefined

  return (
    <main className="ctx-scroll flex min-w-0 flex-1 flex-col overflow-y-auto">
      <DocumentHeader d={d} job={job} />

      <div className="flex-1 space-y-6 p-5">
        <ProcessSection d={d} job={job} />
        <SummarySection d={d} />
        <QuestionsSection questions={d.questions} />
        <ChunksSection chunks={chunks} />
      </div>
    </main>
  )
}