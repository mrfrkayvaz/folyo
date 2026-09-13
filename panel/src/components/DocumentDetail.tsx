import { useState } from "react"
import ChunksSection from "@/components/document/ChunksSection"
import DocumentHeader from "@/components/document/DocumentHeader"
import LogsSection from "@/components/document/LogsSection"
import ProcessSection from "@/components/document/ProcessSection"
import QuestionsSection from "@/components/document/QuestionsSection"
import SummarySection from "@/components/document/SummarySection"
import type { DocumentDetailResponse } from "@/types/models"

type DetailTab = "genel" | "parcalar" | "loglar"

const TABS: ReadonlyArray<{ id: DetailTab; label: string }> = [
  { id: "genel", label: "Genel Bilgiler" },
  { id: "parcalar", label: "Parçalar" },
  { id: "loglar", label: "Loglar" },
]

interface DocumentDetailProps {
  data: DocumentDetailResponse | null
  loading: boolean
}

export default function DocumentDetail({ data, loading }: DocumentDetailProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("genel")

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

  const { document: d, chunks, logs } = data
  const job = d.process?.job ?? undefined

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <DocumentHeader d={d} job={job} />

      <div className="flex flex-1 flex-col px-5 pb-5">
        <div role="tablist" className="tabs tabs-border mt-3 w-fit">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              className={`tab ${activeTab === t.id ? "tab-active text-base-content" : "text-base-content/50"}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
              {t.id === "parcalar" && chunks?.length > 0 && (
                <span className="ml-1.5 text-[10px] text-base-content/45">{chunks.length}</span>
              )}
              {t.id === "loglar" && (logs?.length ?? 0) > 0 && (
                <span className="ml-1.5 text-[10px] text-base-content/45">{logs!.length}</span>
              )}
            </button>
          ))}
        </div>

        <div className="ctx-scroll mt-4 flex min-h-0 flex-1 flex-col overflow-y-auto">
          {activeTab === "genel" && (
            <div className="space-y-6 pr-1">
              <ProcessSection d={d} job={job} />
              <SummarySection d={d} />
              <QuestionsSection questions={d.questions} />
            </div>
          )}
          {activeTab === "parcalar" && <ChunksSection chunks={chunks} />}
          {activeTab === "loglar" && <LogsSection logs={logs} />}
        </div>
      </div>
    </main>
  )
}