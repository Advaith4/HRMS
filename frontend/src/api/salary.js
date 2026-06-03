import api from './axios'

export const getSalaryHistory = async (employeeId) => {
  const response = await api.get(`/api/salary/employee/${employeeId}`)
  return response.data
}

export const addSalaryRevision = async (employeeId, data) => {
  // data: { new_salary, reason, effective_date }
  const response = await api.post(`/api/salary/employee/${employeeId}`, data)
  return response.data
}
