import React from 'react'
import InterviewWorkspaceShell from './InterviewWorkspaceShell'
import { transcribeAudio } from '../../api/interview'
import { submitMockAnswer, completeMockInterview } from '../../api/mock_interview'

export default function MockInterviewWorkspace({ session, onEnd }) {
  // Mock interviews do not strictly enforce proctoring violations to end the session,
  // but we can log them or just ignore them for practice.
  const handleRecordProctoringViolation = async (sessionId, type, detail) => {
    console.log('Mock Interview Proctoring Violation:', type, detail)
    return { success: true }
  }

  return (
    <InterviewWorkspaceShell
      session={session}
      onEnd={onEnd}
      onSubmitAnswer={submitMockAnswer}
      onTranscribeAudio={transcribeAudio}
      onRecordProctoringViolation={handleRecordProctoringViolation}
      onCompleteSession={completeMockInterview}
    />
  )
}
