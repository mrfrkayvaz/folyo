export function formatTs(iso) {
  if (!iso) return ""
  return new Date(iso).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "medium" })
}