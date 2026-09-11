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

export {}
