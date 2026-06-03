import api from './axios'

export const listDesignations = async (deptId) => {
  const response = await api.get('/api/designations', {
    params: deptId ? { department_id: deptId } : {},
  })
  return response.data
}

export const createDesignation = async (data) => {
  const response = await api.post('/api/designations', data)
  return response.data
}

export const updateDesignation = async (id, data) => {
  const response = await api.put(`/api/designations/${id}`, data)
  return response.data
}

export const archiveDesignation = async (id) => {
  const response = await api.delete(`/api/designations/${id}`)
  return response.data
}
