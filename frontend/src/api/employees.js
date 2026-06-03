import api from './axios'

export const listEmployees = async () => {
  const response = await api.get('/api/employees')
  return response.data
}

export const getEmployee = async (employeeId) => {
  const response = await api.get(`/api/employees/${employeeId}`)
  return response.data
}

export const getMyEmployeeProfile = async () => {
  const response = await api.get('/api/employees/me')
  return response.data
}

export const getEmployeeDashboard = async () => {
  const response = await api.get('/api/employees/dashboard')
  return response.data
}

export const checkIn = async () => {
  const response = await api.post('/api/employees/attendance/check-in')
  return response.data
}

export const checkOut = async () => {
  const response = await api.post('/api/employees/attendance/check-out')
  return response.data
}

export const getAttendanceHistory = async () => {
  const response = await api.get('/api/employees/attendance')
  return response.data
}

export const submitLeave = async (leaveData) => {
  // leaveData: { leave_type, start_date, end_date, reason }
  const response = await api.post('/api/employees/leave', leaveData)
  return response.data
}

export const getMyLeaves = async () => {
  const response = await api.get('/api/employees/leave/me')
  return response.data
}

export const listLeaveRequests = async () => {
  const response = await api.get('/api/employees/leave')
  return response.data
}

export const decideLeaveRequest = async (leaveId, decisionData) => {
  // decisionData: { status, manager_note }
  const response = await api.post(`/api/employees/leave/${leaveId}/decision`, decisionData)
  return response.data
}

export const getMySkillGap = async () => {
  const response = await api.get('/api/employees/skill-gap/me')
  return response.data
}

export const analyzeSkillGap = async (roleExpectations) => {
  // roleExpectations: { role_expectations }
  const response = await api.post('/api/employees/skill-gap/me/analyze', {
    role_expectations: roleExpectations,
  })
  return response.data
}

export const askHRAssistant = async (question) => {
  // question: { question }
  const response = await api.post('/api/employees/assistant', { question })
  return response.data
}

export const listEmployeeDirectory = async (params) => {
  const response = await api.get('/api/employees/directory', { params })
  return response.data
}

export const getEmployeeProfile = async (employeeId) => {
  const response = await api.get(`/api/employees/${employeeId}/profile`)
  return response.data
}

export const updateEmployeeProfile = async (employeeId, data) => {
  const response = await api.put(`/api/employees/${employeeId}/profile`, data)
  return response.data
}

