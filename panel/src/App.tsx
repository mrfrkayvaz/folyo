import { useEffect, useState } from "react"
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
  const logout = useAuth((s) => s.logout)
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
    <div className="flex h-dvh bg-base-100 text-base-content">
      <button
        type="button"
        onClick={logout}
        title="Çıkış yap"
        className="btn btn-ghost btn-sm fixed right-3 top-3 z-50 gap-1.5 text-base-content/60 hover:text-base-content"
      >
        <span className="max-w-32 truncate text-xs">{username}</span>
        <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
      </button>
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