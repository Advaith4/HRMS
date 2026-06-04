import api from './axios'

export const listOnboardingTemplates = () =>
  api.get('/api/onboarding/templates').then(r => r.data)

export const createOnboardingTemplate = (data) =>
  api.post('/api/onboarding/templates', data).then(r => r.data)

export const updateOnboardingTemplate = (id, data) =>
  api.put(`/api/onboarding/templates/${id}`, data).then(r => r.data)

export const deleteOnboardingTemplate = (id) =>
  api.delete(`/api/onboarding/templates/${id}`).then(r => r.data)

export const addOnboardingTask = (templateId, data) =>
  api.post(`/api/onboarding/templates/${templateId}/tasks`, data).then(r => r.data)

export const updateOnboardingTask = (taskId, data) =>
  api.put(`/api/onboarding/tasks/${taskId}`, data).then(r => r.data)

export const deleteOnboardingTask = (taskId) =>
  api.delete(`/api/onboarding/tasks/${taskId}`).then(r => r.data)

export const assignOnboardingTemplate = (data) =>
  api.post('/api/onboarding/assign', data).then(r => r.data)

export const getEmployeeOnboarding = (employeeId) =>
  api.get(`/api/onboarding/employee/${employeeId}`).then(r => r.data)

export const updateOnboardingTaskStatus = (planId, taskId, data) =>
  api.put(`/api/onboarding/plan/${planId}/task/${taskId}`, data).then(r => r.data)

export const getOnboardingSummary = () =>
  api.get('/api/onboarding/summary').then(r => r.data)
