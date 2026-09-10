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
 * @property {Object|null} [stats]
 * @property {string|null} [summary]
 * @property {string[]} [starter_questions]
 */

export const createAttachment = ({ id, docId, name, size, status = DocumentStatus.UPLOADING, progress = 0 }) => ({
  id,
  docId,
  name,
  size,
  status,
  progress,
})
