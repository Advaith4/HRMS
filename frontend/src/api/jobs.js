import api from './axios'

export const listJobs = async () => {
  const response = await api.get('/api/jobs')
  return response.data
}

export const getJob = async (jobId) => {
  const response = await api.get(`/api/jobs/${jobId}`)
  return response.data
}

export const createJob = async (jobData) => {
  // jobData: { title, description, required_skills, department, salary_range, experience_required }
  const response = await api.post('/api/jobs', jobData)
  return response.data
}

export const updateJob = async (jobId, jobData) => {
  const response = await api.put(`/api/jobs/${jobId}`, jobData)
  return response.data
}

export const deleteJob = async (jobId) => {
  const response = await api.delete(`/api/jobs/${jobId}`)
  return response.data
}
