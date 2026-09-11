import { useEffect, useState } from "react"
import { getDocumentFileUrlAction } from "../actions/documentActions.js"

const IMAGE_RE = /\.(png|jpe?g|webp|bmp|tiff?)$/i

export function useFilePreview(attachment) {
  const [content, setContent] = useState(null)
  const [pdfUrl, setPdfUrl] = useState(null)
  const [imageUrl, setImageUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const filename = attachment?.filename || attachment?.file?.name || "Dosya"
  const size = attachment?.size ?? attachment?.file?.size
  const isPdf = filename.toLowerCase().endsWith(".pdf")
  const isImage = IMAGE_RE.test(filename)
  const targetPage = attachment?.targetPage ?? null

  useEffect(() => {
    if (!attachment) return

    let isMounted = true
    let createdUrl = null

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
          const res = await fetch(getDocumentFileUrlAction(attachment.docId))
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
        if (isMounted) setError(err.message || "İçerik yüklenirken bir hata oluştu.")
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    loadContent()
    return () => {
      isMounted = false
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [attachment, isPdf])

  return { content, pdfUrl, imageUrl, loading, error, isPdf, isImage, targetPage, filename, size }
}