export interface ChunkItem {
  id: string
  doc_id: string
  chunk_index: number
  page_number: number
  content_type: string
  name?: string
  section_title?: string
  image_path?: string
  page_context?: string
  breadcrumbs?: string[]
  text: string
}