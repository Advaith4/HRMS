import api from './axios'

// Phase 1: Interview API Client
// These endpoints match the backend interview engine at src/api/routes/interview.py

/**
 * Start a new interview session (manual mode - no resume required)
 * POST /api/interview/start
 * Response: { session_id, question, focus_area, focus_type, interviewer_signal, pressure_level, answer_expectation, training_mode, interviewer_persona, persona, coach_memory, session_intro, phase, phase_goal, db_id }
 */
export const startInterview = async (data) => {
  const response = await api.post('/api/interview/start', {
    role: data.role || 'Software Engineer',
    difficulty: data.difficulty || 5,
    weak_areas: data.weak_areas || [],
    training_mode: data.training_mode || 'adaptive',
    interviewer_persona: data.interviewer_persona || 'balanced',
    domain_focus: data.domain_focus || '',
  }, {
    timeout: 60000,
  })
  return response.data
}

/**
 * Start a resume-aware interview session (requires logged-in user with resume)
 * POST /api/interview/start-from-resume
 * Response: { session_id, question, db_id, personalized, role, difficulty, weak_areas, section_scores, resume_score, focus_area, focus_type, interviewer_signal, pressure_level, answer_expectation, question_mix, training_mode, interviewer_persona, persona, coach_memory, session_intro, phase, phase_goal }
 */
export const startInterviewFromResume = async (data) => {
  const response = await api.post('/api/interview/start-from-resume', {
    role: data.role || '',
    difficulty: data.difficulty || 5,
    force_reanalyze: data.force_reanalyze || false,
    training_mode: data.training_mode || 'adaptive',
    interviewer_persona: data.interviewer_persona || 'balanced',
    domain_focus: data.domain_focus || '',
  }, {
    timeout: 60000,
  })
  return response.data
}

/**
 * Submit an answer and get evaluation + next question
 * POST /api/interview/answer
 * Request: { session_id, answer }
 * Response: { evaluation, difficulty, focus_area, focus_type, weak_areas, question_mix, training_mode, interviewer_persona, persona, feedback_message, feedback, answer_expectation, session_turn, coach_memory, avg_score, phase, phase_goal, phase_focus, phase_history, interview_complete, final_feedback, final_verdict, verdict_explanation }
 */
export const submitAnswer = async (sessionId, answer) => {
  const response = await api.post('/api/interview/answer', {
    session_id: sessionId,
    answer: answer,
  }, {
    timeout: 60000,
  })
  return response.data
}

/**
 * Get available interview modes and personas
 * GET /api/interview/modes
 * Response: { training_modes, personas }
 */
export const getInterviewModes = async () => {
  const response = await api.get('/api/interview/modes')
  return response.data
}

/**
 * Get coaching memory for the current user
 * GET /api/interview/coach-memory
 * Response: { success, memory, training_modes, personas }
 */
export const getCoachMemory = async () => {
  const response = await api.get('/api/interview/coach-memory')
  return response.data
}

/**
 * Get daily coaching plan
 * GET /api/interview/daily-plan
 * Response: { success, plan, memory }
 */
export const getDailyPlan = async () => {
  const response = await api.get('/api/interview/daily-plan')
  return response.data
}

/**
 * List all past interview sessions for current user
 * GET /api/interview/sessions
 * Response: [ { session_token, role, difficulty, training_mode, interviewer_persona, avg_score, status, created_at, message_count } ... ]
 */
export const listSessions = async () => {
  const response = await api.get('/api/interview/sessions')
  return response.data
}

/**
 * Get full message history for a specific session
 * GET /api/interview/sessions/{session_id}
 * Response: { session_token, messages[], role, difficulty, training_mode, interviewer_persona, avg_score, status, created_at, updated_at }
 */
export const getSession = async (sessionId) => {
  const response = await api.get(`/api/interview/sessions/${sessionId}`)
  return response.data
}

/**
 * Delete a specific interview session
 * DELETE /api/interview/sessions/{session_id}
 */
export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/api/interview/sessions/${sessionId}`)
  return response.data
}

/**
 * Abandon an active interview session
 * POST /api/interview/{session_id}/abandon
 */
export const abandonSession = async (sessionId) => {
  const response = await api.post(`/api/interview/${sessionId}/abandon`)
  return response.data
}

/**
 * Run credibility analysis comparing resume claims against interview evidence
 * POST /api/interview/{session_id}/credibility
 * Response: { credibility_score, supported_claims, weak_claims, missing_evidence, followup_topics, resume_score, interview_avg_score, recommendation, status }
 */
export const getCredibilityReport = async (sessionId, force = false) => {
  const response = await api.post(`/api/interview/${sessionId}/credibility`, null, {
    params: { force },
  })
  return response.data
}

/**
 * Transcribe an audio blob using Groq Whisper
 * POST /api/interview/transcribe (multipart/form-data)
 * Response: { transcript }
 */
// ── Phase 5: Interview Intelligence Dashboard ───────────────────────────────

/**
 * Get ranked candidate leaderboard
 * GET /api/interview/intelligence/leaderboard
 */
export const getIntelligenceLeaderboard = async () => {
  const response = await api.get('/api/interview/intelligence/leaderboard')
  return response.data
}

/**
 * Full intelligence report for a candidate
 * GET /api/interview/intelligence/report/{candidate_id}
 */
export const getCandidateIntelligenceReport = async (candidateId) => {
  const response = await api.get(`/api/interview/intelligence/report/${candidateId}`)
  return response.data
}

/**
 * Compare two or more candidates side-by-side
 * POST /api/interview/intelligence/compare
 */
export const compareCandidates = async (candidateIds) => {
  const response = await api.post('/api/interview/intelligence/compare', { candidate_ids: candidateIds })
  return response.data
}

/**
 * Get top candidates by various metrics
 * GET /api/interview/intelligence/top-candidates
 */
export const getTopCandidates = async () => {
  const response = await api.get('/api/interview/intelligence/top-candidates')
  return response.data
}

/**
 * Get follow-up questions for next interview round
 * GET /api/interview/intelligence/followup-questions/{session_id}
 */
export const getFollowupQuestions = async (sessionId) => {
  const response = await api.get(`/api/interview/intelligence/followup-questions/${sessionId}`)
  return response.data
}

/**
 * Advance a candidate to next stage
 * POST /api/interview/intelligence/{session_id}/advance
 */
export const advanceCandidate = async (sessionId) => {
  const response = await api.post(`/api/interview/intelligence/${sessionId}/advance`)
  return response.data
}

/**
 * Reject a candidate
 * POST /api/interview/intelligence/{session_id}/reject
 */
export const rejectCandidate = async (sessionId) => {
  const response = await api.post(`/api/interview/intelligence/${sessionId}/reject`)
  return response.data
}

export const transcribeAudio = async (audioBlob) => {
  const formData = new FormData()
  formData.append('audio_file', audioBlob, 'recording.webm')
  const response = await api.post('/api/interview/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return response.data
}

/**
 * Start/resume a mandatory interview linked to a job application
 * POST /api/interview/start-for-application
 */
export const startInterviewForApplication = async (applicationId) => {
  const response = await api.post('/api/interview/start-for-application', {
    application_id: applicationId,
    difficulty: 5,
    training_mode: 'domain_specific',
    interviewer_persona: 'balanced'
  }, {
    timeout: 60000,
  })
  return response.data
}

/**
 * Record a proctoring violation for an active interview session
 * POST /api/interview/{session_id}/violation
 */
export const recordProctoringViolation = async (sessionId, type, detail) => {
  const response = await api.post(`/api/interview/${sessionId}/violation`, {
    violation_type: type,
    detail: detail
  })
  return response.data
}
