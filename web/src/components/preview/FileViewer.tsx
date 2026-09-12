interface FileViewerProps {
  loading: boolean
  error: string | null
  isPdf: boolean
  isImage: boolean
  pdfUrl: string | null
  imageUrl: string | null
  content: string | null
  filename: string
  targetPage?: number | null
}

export default function FileViewer({
  loading,
  error,
  isPdf,
  isImage,
  pdfUrl,
  imageUrl,
  content,
  filename,
  targetPage,
}: FileViewerProps) {
  if (loading) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 p-4 text-center sm:p-6">
        <span className="loading loading-spinner loading-md text-primary" />
        <p className="text-xs text-base-content/50">Dosya yükleniyor…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-2 p-4 text-center text-error sm:p-6">
        <p className="text-sm font-medium">⚠️ {error}</p>
      </div>
    )
  }

  if (isPdf && pdfUrl) {
    return (
      <iframe
        src={targetPage ? `${pdfUrl}#page=${targetPage}` : pdfUrl}
        className="block h-[75vh] min-h-[300px] w-full border-0 bg-base-200"
        title={filename}
      />
    )
  }

  if (isImage && imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={filename}
        className="block max-h-[75vh] w-full bg-base-200 object-contain p-2"
      />
    )
  }

  return (
    <pre className="m-0 min-h-[300px] flex-1 whitespace-pre-wrap break-words border-0 rounded-none bg-base-200/50 p-4 font-mono text-xs leading-relaxed text-base-content/90 sm:p-6 sm:text-sm">
      {content}
    </pre>
  )
}