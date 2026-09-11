import { useEffect, useState } from "react"
import WorkspaceList from "./components/WorkspaceList.jsx"
import DocumentList from "./components/DocumentList.jsx"
import DocumentDetail from "./components/DocumentDetail.jsx"
import { listWorkspaces, getWorkspace, getDocument } from "./lib/api.js"

export default function App() {
  const [workspaces, setWorkspaces] = useState([])
  const [activeWsId, setActiveWsId] = useState(null)
  const [workspaceData, setWorkspaceData] = useState(null)
  const [activeDocId, setActiveDocId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadingWs, setLoadingWs] = useState(false)
  const [loadingDoc, setLoadingDoc] = useState(false)

  useEffect(() => {
    listWorkspaces()
      .then((d) => setWorkspaces(d.workspaces || []))
      .catch(() => {})
  }, [])

  const selectWorkspace = async (id) => {
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

  const selectDocument = async (id) => {
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
      <WorkspaceList workspaces={workspaces} activeId={activeWsId} onSelect={selectWorkspace} />
      <DocumentList
        docs={workspaceData?.documents || null}
        activeDocId={activeDocId}
        loading={loadingWs}
        onSelect={selectDocument}
      />
      <DocumentDetail data={detail} loading={loadingDoc} />
    </div>
  )
}