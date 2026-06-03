import api from './axios'

export const listCandidates = async () => {
  const response = await api.get('/api/candidates')
  return response.data
}

export const getCandidate = async (candidateId) => {
  const response = await api.get(`/api/candidates/${candidateId}`)
  return response.data
}
