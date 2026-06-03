import api from './axios'

export const applyToJob = async (jobId, file) => {
  const formData = new FormData()
  formData.append('job_id', jobId)
  formData.append('file', file)

  const response = await api.post('/api/applications/apply', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000, // 60s — file upload + pypdf parsing can take a moment
  })
  return response.data
}

export const getMyApplications = async () => {
  const response = await api.get('/api/applications/me')
  return response.data
}

export const listApplications = async () => {
  const response = await api.get('/api/applications')
  return response.data
}

export const reanalyzeApplication = async (applicationId) => {
  const response = await api.post(`/api/applications/${applicationId}/analyze`)
  return response.data
}

export const hireCandidate = async (applicationId, hireData) => {
  // hireData: { department, designation, salary, joining_date, employee_code }
  const response = await api.post(`/api/applications/${applicationId}/hire`, hireData)
  return response.data
}

export const getJobRankings = async (jobId) => {
  const response = await api.get(`/api/applications/rankings/${jobId}`)
  return response.data
}
