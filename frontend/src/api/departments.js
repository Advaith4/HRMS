import api from './axios'

export const listDepartments = async () => {
  const response = await api.get('/api/departments')
  return response.data
}

export const createDepartment = async (data) => {
  const response = await api.post('/api/departments', data)
  return response.data
}

export const updateDepartment = async (id, data) => {
  const response = await api.put(`/api/departments/${id}`, data)
  return response.data
}

export const deactivateDepartment = async (id) => {
  const response = await api.delete(`/api/departments/${id}`)
  return response.data
}
