import api from './axios'

/**
 * Fetches jobs + applications + candidates in a single HTTP request.
 * The backend runs 5 optimised batch queries instead of 3N+1.
 * Replaces separate listJobs() + listApplications() + listCandidates() calls.
 */
export const getHRDashboardData = async () => {
  const response = await api.get('/api/dashboard/hr')
  return response.data
}

/**
 * Fetches all jobs + this candidate's applications + resume status in one request.
 * Replaces separate listJobs() + getMyApplications() + getMyResume() calls.
 */
export const getCandidateDashboardData = async () => {
  const response = await api.get('/api/dashboard/candidate')
  return response.data
}
