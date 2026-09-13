import { useEffect, useState } from "react"
import { getDocumentFileUrlAction } from "../actions/index"
import { authHeaders } from "../lib/http"
import type { Attachment } from "../types/attachmentTypes"

const IMAGE_RE = /\.(png|jpe?g|webp|bmp|tiff?)$/i

export interface FilePreview {
  content: string | null
  pdfUrl: string | null
  imageUrl: string | null
  loading: boolean
  error: string | null
  isPdf: boolean
  isImage: boolean
  targetPage: number | null
  filename: string
  size?: number
}

export function useFilePreview(attachment?: Attachment | null): FilePreview {
  const [content, setContent] = useState<string | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const filename = attachment?.filename || attachment?.file?.name || "Dosya"
  const size = attachment?.size ?? attachment?.file?.size
  const isPdf = filename.toLowerCase().endsWith(".pdf")
  const isImage = IMAGE_RE.test(filename)
  const targetPage = attachment?.targetPage ?? null

  useEffect(() => {
    if (!attachment) return

    let isMounted = true
    let createdUrl: string | null = null

    const loadContent = async () => {
      setLoading(true)
      setError(null)
      setContent(null)
      setPdfUrl(null)
      setImageUrl(null)

      try {
        if (attachment.file) {
          if (isPdf) {
            createdUrl = URL.createObjectURL(attachment.file)
            if (isMounted) setPdfUrl(createdUrl)
          } else if (isImage) {
            createdUrl = URL.createObjectURL(attachment.file)
            if (isMounted) setImageUrl(createdUrl)
          } else {
            const text = await attachment.file.text()
            if (isMounted) setContent(text)
          }
        } else if (attachment.docId) {
          const res = await fetch(getDocumentFileUrlAction(attachment.docId), { headers: authHeaders() })
          if (!res.ok) throw new Error(`Dosya içeriği alınamadı (HTTP ${res.status})`)

          if (isPdf) {
            const blob = await res.blob()
            createdUrl = URL.createObjectURL(blob)
            if (isMounted) setPdfUrl(createdUrl)
          } else if (isImage) {
            const blob = await res.blob()
            createdUrl = URL.createObjectURL(blob)
            if (isMounted) setImageUrl(createdUrl)
          } else {
            const text = await res.text()
            if (isMounted) setContent(text)
          }
        } else {
          throw new Error("Dosya içeriğine erişilemedi.")
        }
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : "İçerik yüklenirken bir hata oluştu.")
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    void loadContent()
    return () => {
      isMounted = false
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
    // attachment nesnesi değişince yeniden yükle; isPdf türevdir
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attachment])

  return { content, pdfUrl, imageUrl, loading, error, isPdf, isImage, targetPage, filename, size }
}