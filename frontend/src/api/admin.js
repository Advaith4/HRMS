import api from './axios'

export const getAdminUsers = async () => {
  const response = await api.get('/api/admin/users')
  return response.data
}

export const updateAdminUser = async (userId, data) => {
  const response = await api.put(`/api/admin/users/${userId}`, data)
  return response.data
}

export const getAdminPolicies = async () => {
  const response = await api.get('/api/admin/policies')
  return response.data
}

export const createAdminPolicy = async (data) => {
  const response = await api.post('/api/admin/policies', data)
  return response.data
}

export const updateAdminPolicy = async (filename, data) => {
  const response = await api.put(`/api/admin/policies/${filename}`, data)
  return response.data
}

export const deleteAdminPolicy = async (filename) => {
  const response = await api.delete(`/api/admin/policies/${filename}`)
  return response.data
}

export const reindexAdminPolicy = async (filename) => {
  const response = await api.post(`/api/admin/policies/${filename}/reindex`)
  return response.data
}

export const getAdminKnowledge = async () => {
  const response = await api.get('/api/admin/knowledge')
  return response.data
}

export const createAdminKnowledge = async (data) => {
  const response = await api.post('/api/admin/knowledge', data)
  return response.data
}

export const updateAdminKnowledge = async (category, filename, data) => {
  const response = await api.put(`/api/admin/knowledge/${category}/${filename}`, data)
  return response.data
}

export const deleteAdminKnowledge = async (category, filename) => {
  const response = await api.delete(`/api/admin/knowledge/${category}/${filename}`)
  return response.data
}

export const reindexAdminKnowledge = async (category, filename) => {
  const response = await api.post(`/api/admin/knowledge/${category}/${filename}/reindex`)
  return response.data
}
