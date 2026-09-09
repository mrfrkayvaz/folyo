import { ChatRole } from "../enums/chatEnums.js"

/**
 * @typedef {Object} CitationSource
 * @property {string} label
 * @property {string} [meta]
 */

/**
 * @typedef {Object} ChatMessageItem
 * @property {string} id
 * @property {'user'|'assistant'} role
 * @property {string} content
 * @property {CitationSource[]|null} [citations]
 * @property {string} created_at
 */

export const createMessage = ({ id = crypto.randomUUID(), role = ChatRole.USER, text = "", streaming = false }) => ({
  id,
  role,
  text,
  streaming,
  sources: [],
})
