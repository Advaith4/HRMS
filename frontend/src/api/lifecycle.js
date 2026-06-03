import api from './axios'

export const getLifecycle = async (employeeId) => {
  const response = await api.get(`/api/lifecycle/employee/${employeeId}`)
  return response.data
}

export const addLifecycleEvent = async (employeeId, data) => {
  // data: { event_type, event_date, description }
  const response = await api.post(`/api/lifecycle/employee/${employeeId}`, data)
  return response.data
}
