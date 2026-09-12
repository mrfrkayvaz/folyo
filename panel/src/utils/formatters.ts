export function formatTs(iso?: string): string {
  if (!iso) return ""
  return new Date(iso).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "medium" })
}