import api from './axios'

export const getMyProfileCompletion = () =>
  api.get('/api/profile/me').then(r => r.data)

export const updateCandidateProfile = (data) =>
  api.put('/api/profile/candidate', data).then(r => r.data)

export const updateEmployeeCompletionProfile = (data) =>
  api.put('/api/profile/employee', data).then(r => r.data)

export const uploadProfileDocument = (documentType, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/profile/documents', formData, {
    params: { document_type: documentType },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  }).then(r => r.data)
}

export const listReviewDocuments = () =>
  api.get('/api/profile/documents/review').then(r => r.data)

export const decideProfileDocument = (kind, documentId, data) =>
  api.put(`/api/profile/documents/${kind}/${documentId}/decision`, data).then(r => r.data)

export const downloadProfileDocumentUrl = (kind, documentId) =>
  `/api/profile/documents/${kind}/${documentId}/download`
