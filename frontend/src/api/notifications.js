import api from './axios'

export const listNotifications = async () => {
  const response = await api.get('/api/notifications')
  return response.data
}

export const markRead = async (id) => {
  const response = await api.put(`/api/notifications/${id}/read`)
  return response.data
}

export const markAllRead = async () => {
  const response = await api.put('/api/notifications/read-all')
  return response.data
}
