import api from './axios'

export const startMockInterview = async (data) => {
  const response = await api.post('/api/mock-interview/start', {
    role: data.role || 'Software Engineer',
    difficulty: data.difficulty || 5,
    training_mode: data.training_mode || 'adaptive',
    interviewer_persona: data.interviewer_persona || 'balanced',
    domain_focus: data.domain_focus || '',
    interview_type: data.interview_type || 'mixed',
    resume_source: data.resume_source || 'none',
    force_reanalyze: data.force_reanalyze || false
  }, {
    timeout: 60000,
  })
  return response.data
}

export const submitMockAnswer = async (sessionId, answer) => {
  const response = await api.post('/api/mock-interview/answer', {
    session_id: sessionId,
    answer: answer,
  }, {
    timeout: 60000,
  })
  return response.data
}

export const completeMockInterview = async (sessionId) => {
  const response = await api.post(`/api/mock-interview/${sessionId}/complete`, {}, {
    timeout: 60000,
  })
  return response.data
}

export const listMockSessions = async () => {
  const response = await api.get('/api/mock-interview/sessions')
  return response.data
}
