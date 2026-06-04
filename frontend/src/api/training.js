import api from './axios'

export const listTrainingPrograms = () =>
  api.get('/api/training/programs').then(r => r.data)

export const createTrainingProgram = (data) =>
  api.post('/api/training/programs', data).then(r => r.data)

export const updateTrainingProgram = (id, data) =>
  api.put(`/api/training/programs/${id}`, data).then(r => r.data)

export const archiveTrainingProgram = (id) =>
  api.delete(`/api/training/programs/${id}`).then(r => r.data)

export const assignTraining = (data) =>
  api.post('/api/training/assign', data).then(r => r.data)

export const listTrainingAssignments = () =>
  api.get('/api/training/assignments').then(r => r.data)

export const getMyTrainingAssignments = () =>
  api.get('/api/training/assignments/my').then(r => r.data)

export const getTeamTrainingAssignments = () =>
  api.get('/api/training/assignments').then(r => r.data)

export const updateTrainingProgress = (assignmentId, data) =>
  api.put(`/api/training/assignments/${assignmentId}/progress`, data).then(r => r.data)

export const getTrainingSummary = () =>
  api.get('/api/training/summary').then(r => r.data)
