import api from './axios'

export const sendRagChatMessage = async (query) => {
  const response = await api.post('/api/rag/chat', { query })
  return response.data
}
