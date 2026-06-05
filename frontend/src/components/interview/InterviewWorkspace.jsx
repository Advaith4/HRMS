import React from 'react'
import InterviewWorkspaceShell from './InterviewWorkspaceShell'
import { submitAnswer, transcribeAudio, recordProctoringViolation, abandonSession } from '../../api/interview'

export default function InterviewWorkspace({ session, onEnd }) {
  // We use the wrapper to bind the official API calls
  return (
    <InterviewWorkspaceShell
      session={session}
      onEnd={onEnd}
      onSubmitAnswer={submitAnswer}
      onTranscribeAudio={transcribeAudio}
      onRecordProctoringViolation={recordProctoringViolation}
      onCompleteSession={abandonSession}
    />
  )
}
