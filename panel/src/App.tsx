import { useEffect, useState } from "react"
import { Route, Routes } from "react-router-dom"
import IconRail from "@/components/IconRail"
import QaLogsView from "@/components/QaLogsView"
import WorkspaceList from "@/components/WorkspaceList"
import DocumentList from "@/components/DocumentList"
import DocumentDetail from "@/components/DocumentDetail"
import Login from "@/components/Login"
import { authMe, listWorkspaces, getWorkspace, getDocument } from "@/lib/api"
import { useAuth } from "@/store/auth"
import type { PanelWorkspace, PanelDocument, DocumentDetailResponse } from "@/types/models"

export default function App() {
  const token = useAuth((s) => s.token)
  const username = useAuth((s) => s.username)
  const [workspaces, setWorkspaces] = useState<PanelWorkspace[]>([])
  const [activeWsId, setActiveWsId] = useState<string | null>(null)
  const [workspaceData, setWorkspaceData] = useState<Awaited<ReturnType<typeof getWorkspace>> | null>(null)
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null)
  const [loadingWs, setLoadingWs] = useState(false)
  const [loadingDoc, setLoadingDoc] = useState(false)

  // Oturum geri yükleme: localStorage'daki token varsa sunucuda doğrula;
  // geçersiz/süresi dolmuşsa temizle (giriş ekranına düşer).
  useEffect(() => {
    if (useAuth.getState().token) {
      authMe().catch(() => useAuth.getState().logout())
    }
  }, [])

  useEffect(() => {
    if (!token) return
    listWorkspaces()
      .then((d) => setWorkspaces(d.workspaces ?? []))
      .catch(() => {})
  }, [token])

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

  if (!token) {
    return <Login />
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-base-100 text-base-content">
      <IconRail />
      <Routes>
        <Route path="/logs" element={<QaLogsView />} />
        {/* Anasayfa: sohbetler (workspace → doküman → detay) */}
        <Route
          path="*"
          element={
            <>
              <WorkspaceList workspaces={workspaces} activeId={activeWsId} onSelect={(id) => void selectWorkspace(id)} />
              <DocumentList
                docs={workspaceData?.documents ?? null}
                activeDocId={activeDocId}
                loading={loadingWs}
                onSelect={(id) => void selectDocument(id)}
              />
              <DocumentDetail data={detail} loading={loadingDoc} />
            </>
          }
        />
      </Routes>
    </div>
  )
}