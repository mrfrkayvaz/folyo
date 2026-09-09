import { DocumentStatus } from "../enums/documentEnums.js"

/**
 * @typedef {Object} DocumentItem
 * @property {string} id
 * @property {string} filename
 * @property {string} file_type
 * @property {number} size
 * @property {string} status
 * @property {number} chunk_count
 * @property {string|null} [error]
 */

export const createAttachment = ({ id, docId, name, size, status = DocumentStatus.UPLOADING, progress = 0 }) => ({
  id,
  docId,
  name,
  size,
  status,
  progress,
})
