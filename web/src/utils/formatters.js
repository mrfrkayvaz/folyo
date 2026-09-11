export function formatBytes(bytes) {
  if (!bytes) return ""
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function timeAgo(iso) {
  if (!iso) return ""
  const t = new Date(iso).getTime()
  const diff = Math.max(0, Date.now() - t)
  const m = Math.floor(diff / 60000)
  if (m < 1) return "şimdi"
  if (m < 60) return `${m} dk`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} sa`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d} gün`
  return new Date(iso).toLocaleDateString("tr-TR")
}