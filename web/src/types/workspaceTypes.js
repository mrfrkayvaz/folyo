/**
 * @typedef {Object} Workspace
 * @property {string} id
 * @property {string} name
 * @property {string} created_at
 * @property {string|null} [last_message_at]
 */

export const createEmptyWorkspace = () => ({
  id: "",
  name: "",
  created_at: new Date().toISOString(),
  last_message_at: null,
})
