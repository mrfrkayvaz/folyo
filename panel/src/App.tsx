import { useEffect, useState } from "react"
import WorkspaceList from "./components/WorkspaceList"
import DocumentList from "./components/DocumentList"
import DocumentDetail from "./components/DocumentDetail"
import { listWorkspaces, getWorkspace, getDocument } from "./lib/api"
import type { PanelWorkspace, PanelDocument, DocumentDetailResponse } from "./types/models"

export default function App() {
  const [workspaces, setWorkspaces] = useState<PanelWorkspace[]>([])
  const [activeWsId, setActiveWsId] = useState<string | null>(null)
  const [workspaceData, setWorkspaceData] = useState<Awaited<ReturnType<typeof getWorkspace>> | null>(null)
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null)
  const [loadingWs, setLoadingWs] = useState(false)
  const [loadingDoc, setLoadingDoc] = useState(false)

  useEffect(() => {
    listWorkspaces()
      .then((d) => setWorkspaces(d.workspaces ?? []))
      .catch(() => {})
  }, [])

  const selectWorkspace = async (id: string) => {
    setActiveWsId(id)
    setActiveDocId(null)
    setDetail(null)
    setLoadingWs(true)
    try {
      setWorkspaceData(await getWorkspace(id))
    } catch {
      setWorkspaceData(null)
    } finally {
      setLoadingWs(false)
    }
  }

  const selectDocument = async (id: string) => {
    setActiveDocId(id)
    setDetail(null)
    setLoadingDoc(true)
    try {
      setDetail(await getDocument(id))
    } catch {
      setDetail(null)
    } finally {
      setLoadingDoc(false)
    }
  }

  return (
    <div className="flex h-dvh bg-base-100 text-base-content">
      <WorkspaceList workspaces={workspaces} activeId={activeWsId} onSelect={(id) => void selectWorkspace(id)} />
      <DocumentList
        docs={workspaceData?.documents ?? null}
        activeDocId={activeDocId}
        loading={loadingWs}
        onSelect={(id) => void selectDocument(id)}
      />
      <DocumentDetail data={detail} loading={loadingDoc} />
    </div>
  )
}