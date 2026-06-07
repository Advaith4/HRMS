import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Camera, Monitor, Mic,
  ArrowRight, Edit3, Check, X, Send, AlertTriangle,
  Video, StopCircle, Loader2, Shield, Clock
} from 'lucide-react'
import useRecorder from '../../hooks/useRecorder'
import useInterviewMedia from '../../hooks/useInterviewMedia'
import InterviewSummary from './InterviewSummary'
import MockInterviewSummary from './MockInterviewSummary'
import toast from 'react-hot-toast'

const INTERVIEW_PHASES = [
  'Resume Validation',
  'Technical Assessment',
  'Behavioral Assessment',
  'Final Evaluation',
]

const parseSessionContext = (value) => {
  if (!value) return {}
  if (typeof value === 'object') return value
  try {
    return JSON.parse(value)
  } catch {
    return {}
  }
}

const conversationFromMessages = (sessionData) => {
  const items = []
  if (sessionData?.session_intro) {
    items.push({ type: 'intro', content: sessionData.session_intro, key: 'intro' })
  }
  if (Array.isArray(sessionData?.messages) && sessionData.messages.length > 0) {
    sessionData.messages.forEach((msg, index) => {
      if (msg.role === 'feedback') return
      if (msg.role === 'ai') {
        items.push({ type: 'question', content: msg.content, key: `ai-${index}-${msg.timestamp || index}` })
      } else if (msg.role === 'user') {
        items.push({ type: 'answer', content: msg.content, key: `user-${index}-${msg.timestamp || index}` })
      }
    })
  } else if (sessionData?.question) {
    items.push({ type: 'question', content: sessionData.question, key: 'seed-question' })
  }
  return items
}

export default function InterviewWorkspaceShell({ session, onEnd, onSubmitAnswer, onTranscribeAudio, onRecordProctoringViolation, onCompleteSession, isMock = false }) {
  const {
    cameraStatus, screenShareEnabled, screenShareStatus, screenShareSurface, isMobile,
    cameraVideoRef, screenVideoRef,
    startCamera, stopCamera, startScreenShare, stopScreenShare,
  } = useInterviewMedia()

  const {
    isRecording, duration, audioBlob, audioMeta, error: recorderError,
    startRecording, stopRecording, clearRecording,
  } = useRecorder()

  const [conversation, setConversation] = useState([])
  const [answer, setAnswer] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [showTranscriptReview, setShowTranscriptReview] = useState(false)
  const [micStatus, setMicStatus] = useState('idle')
  const [inputMode, setInputMode] = useState('voice')
  const [currentQuestion, setCurrentQuestion] = useState(session.question || '')
  const [currentPhase, setCurrentPhase] = useState(session.phase || 'Resume Validation')
  const [currentPhaseGoal, setCurrentPhaseGoal] = useState(session.phase_goal || '')
  const [questionCount, setQuestionCount] = useState(1)
  const [sessionDuration, setSessionDuration] = useState(0)
  const [completedSession, setCompletedSession] = useState(null)
  const [completedConversation, setCompletedConversation] = useState([])
  const [completedDuration, setCompletedDuration] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(
    typeof document !== 'undefined' ? Boolean(document.fullscreenElement) : false
  )
  const [proctoringStarted, setProctoringStarted] = useState(false)
  const [setupCompleted, setSetupCompleted] = useState(false)
  const [proctoringError, setProctoringError] = useState('')
  const [violations, setViolations] = useState([])
  
  const [showEndModal, setShowEndModal] = useState(false)
  const [isProcessingEnd, setIsProcessingEnd] = useState(false)

  const messagesEndRef = useRef(null)
  const durationTimerRef = useRef(null)
  const violationsRef = useRef([])
  const proctoringGraceTimersRef = useRef({})
  const proctoringGraceStartedRef = useRef({})
  const transcriptionGenerationRef = useRef(0)

  useEffect(() => {
    setConversation(conversationFromMessages(session))

    const aiMsgs = session?.messages?.filter(m => m.role === 'ai') || []
    if (aiMsgs.length > 0) {
      const lastAi = aiMsgs[aiMsgs.length - 1]
      setCurrentQuestion(lastAi.content || '')
      setCurrentPhase(lastAi.phase || 'Resume Validation')
      setQuestionCount(aiMsgs.length)
    } else {
      setCurrentQuestion(session?.question || '')
      setCurrentPhase(session?.phase || 'Resume Validation')
      setQuestionCount(session?.question ? 1 : 0)
    }
    setCurrentPhaseGoal(session?.phase_goal || '')

    if (session?.status === 'cancelled') {
      setCompletedSession({
        ...session,
        id: session.db_id || session.id
      })
    }
  }, [session])

  useEffect(() => {
    durationTimerRef.current = setInterval(() => {
      setSessionDuration(prev => prev + 1)
    }, 1000)
    return () => {
      if (durationTimerRef.current) clearInterval(durationTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [conversation])

  useEffect(() => {
    if (recorderError) {
      setMicStatus('error')
      setInputMode('text')
      clearRecording()
    }
  }, [recorderError, clearRecording])

  useEffect(() => {
    if (!audioBlob) return
    const generation = transcriptionGenerationRef.current + 1
    transcriptionGenerationRef.current = generation
    const blobId = audioMeta?.blobId || `${audioBlob.size}-${audioBlob.type}`
    const doTranscribe = async () => {
      setIsTranscribing(true)
      try {
        console.info('audio_transcription_state_before_upload', {
          generation,
          blobId,
          blobSizeBytes: audioBlob.size,
          blobType: audioBlob.type,
          audioMeta,
        })
        const result = await onTranscribeAudio(audioBlob, audioMeta?.durationMs ? audioMeta.durationMs / 1000 : duration, blobId)
        if (generation !== transcriptionGenerationRef.current) {
          console.info('audio_transcription_stale_result_ignored', { generation, current: transcriptionGenerationRef.current, blobId })
          return
        }
        console.info('audio_transcription_complete', {
          generation,
          blobId,
          audioMeta,
          confidence: result.confidence,
          processingTimeMs: result.processing_time_ms,
          duration: result.duration,
          model: result.model,
          language: result.language,
          requestId: result.request_id,
          transcriptChars: result.transcript?.length || 0,
        })
        setTranscript(result.transcript || '')
        setShowTranscriptReview(true)
      } catch (err) {
        if (generation !== transcriptionGenerationRef.current) return
        console.error('Transcription failed:', {
          generation,
          blobId,
          error: err,
          status: err?.response?.status,
          detail: err?.response?.data?.detail,
          audioMeta,
          blobSizeBytes: audioBlob.size,
          blobType: audioBlob.type,
        })
        toast.error('Unable to transcribe audio. You can type your answer instead.')
        setInputMode('text')
      } finally {
        if (generation === transcriptionGenerationRef.current) {
          setIsTranscribing(false)
          clearRecording()
        }
      }
    }
    doTranscribe()
  }, [audioBlob, audioMeta, clearRecording, duration, onTranscribeAudio])

  useEffect(() => {
    if (completedSession) {
      stopCamera()
      stopScreenShare()
      stopRecording()
      clearRecording()
    }
  }, [completedSession, stopCamera, stopScreenShare, stopRecording, clearRecording])

  const addViolation = useCallback(async (type, detail) => {
    const startedAt = proctoringGraceStartedRef.current[type] || Date.now()
    const entry = {
      type,
      detail,
      timestamp: new Date().toISOString(),
      duration_ms: Date.now() - startedAt,
    }
    violationsRef.current = [...violationsRef.current, entry].slice(-20)
    setViolations(violationsRef.current)

    try {
      const result = await onRecordProctoringViolation(session.session_id, type, detail, {
        duration_ms: entry.duration_ms,
        severity: entry.duration_ms >= 10000 ? 'high' : 'medium',
      })
      if (result.cancelled) {
        setCompletedSession({
          ...session,
          status: 'cancelled',
          cancellation_reason: result.cancellation_reason || 'Proctoring violation limit exceeded (3).'
        })
        toast.error('Interview cancelled due to proctoring violations.')
      } else {
        toast.warning(`Security alert: ${detail} (${result.violations_count}/3 violations recorded)`)
      }
    } catch (err) {
      console.error('Failed to log violation on backend:', err)
    }
  }, [onRecordProctoringViolation, session])

  const scheduleViolation = useCallback((type, detail, graceMs = 4000) => {
    if (isMock || !setupCompleted || completedSession || proctoringGraceTimersRef.current[type]) return
    proctoringGraceStartedRef.current[type] = Date.now()
    proctoringGraceTimersRef.current[type] = window.setTimeout(() => {
      proctoringGraceTimersRef.current[type] = null
      addViolation(type, detail)
    }, graceMs)
  }, [addViolation, completedSession, setupCompleted, isMock])

  const clearScheduledViolation = useCallback((type) => {
    if (proctoringGraceTimersRef.current[type]) {
      window.clearTimeout(proctoringGraceTimersRef.current[type])
      proctoringGraceTimersRef.current[type] = null
    }
    proctoringGraceStartedRef.current[type] = null
  }, [])

  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement)
      setIsFullscreen(active)
      if (setupCompleted && !active) {
        scheduleViolation('fullscreen_exit', 'Candidate exited fullscreen mode.')
      } else if (active) {
        clearScheduledViolation('fullscreen_exit')
      }
    }
    const handleVisibilityChange = () => {
      if (setupCompleted && document.hidden) {
        scheduleViolation('tab_switch', 'Candidate switched away from the interview tab.')
      } else if (!document.hidden) {
        clearScheduledViolation('tab_switch')
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [clearScheduledViolation, scheduleViolation, setupCompleted])

  useEffect(() => {
    if (setupCompleted && cameraStatus !== 'active') {
      scheduleViolation('camera_off', 'Camera was turned off or became unavailable.')
    } else if (cameraStatus === 'active') {
      clearScheduledViolation('camera_off')
    }
  }, [cameraStatus, clearScheduledViolation, scheduleViolation, setupCompleted])

  useEffect(() => {
    if (setupCompleted && screenShareStatus !== 'active') {
      scheduleViolation('screen_share_off', 'Screen sharing was stopped or became unavailable.')
    } else if (screenShareStatus === 'active') {
      clearScheduledViolation('screen_share_off')
    }
  }, [clearScheduledViolation, scheduleViolation, screenShareStatus, setupCompleted])

  const isEntireScreenShared = !screenShareSurface || screenShareSurface === 'monitor'
  const proctoringReady = isMock ? (cameraStatus === 'active') : (
    proctoringStarted &&
    cameraStatus === 'active' &&
    screenShareStatus === 'active' &&
    isFullscreen &&
    isEntireScreenShared
  )

  useEffect(() => {
    console.info('interview_proctoring_state', {
      sessionId: session?.session_id,
      proctoringStarted,
      proctoringReady,
      setupCompleted,
      cameraStatus,
      screenShareStatus,
      screenShareSurface,
      isFullscreen,
      isEntireScreenShared,
    })
  }, [
    cameraStatus,
    isEntireScreenShared,
    isFullscreen,
    proctoringReady,
    proctoringStarted,
    screenShareStatus,
    screenShareSurface,
    session?.session_id,
    setupCompleted,
  ])

  useEffect(() => {
    if (proctoringReady) {
      setSetupCompleted(true)
    }
  }, [proctoringReady])

  const enterFullscreen = useCallback(async () => {
    if (document.fullscreenElement) return true
    try {
      await document.documentElement.requestFullscreen()
      setIsFullscreen(true)
      return true
    } catch {
      setIsFullscreen(false)
      return false
    }
  }, [])

  const handleStartProctoring = async () => {
    setProctoringError('')
    if (!isMock && screenShareEnabled && !isEntireScreenShared) {
      stopScreenShare()
      setProctoringError('Please start again and choose your entire screen, not a browser tab or window.')
      return
    }
    setProctoringStarted(true)
    const cameraPromise = startCamera()

    if (isMock) {
      const cameraOk = await cameraPromise
      if (!cameraOk) {
        setProctoringError('Camera is required for the mock interview.')
        toast.error('Please enable your camera to continue.')
      }
      return
    }

    const screenPromise = startScreenShare()
    const fullscreenPromise = enterFullscreen()
    const [screenOk, cameraOk, fullscreenOk] = await Promise.all([
      screenPromise,
      cameraPromise,
      fullscreenPromise,
    ])

    if (!cameraOk || !screenOk || !fullscreenOk) {
      setProctoringError('Camera, screen sharing, and browser fullscreen are all required to continue.')
      toast.error('Complete the proctoring setup to continue.')
    }
  }

  const handleStartRecording = async () => {
    if (!proctoringReady) {
      toast.error('Complete proctoring setup before answering.')
      return
    }
    transcriptionGenerationRef.current += 1
    setTranscript('')
    setShowTranscriptReview(false)
    setMicStatus('active')
    const ok = await startRecording()
    if (!ok) {
      setMicStatus('error')
      setInputMode('text')
    }
  }

  const handleStopRecording = () => {
    stopRecording()
  }

  const submitAnswerText = useCallback(async (rawText) => {
    const text = rawText.trim()
    if (!text || !session?.session_id || isSubmitting) return
    if (!proctoringReady) {
      toast.error(
        isMock
          ? 'Please enable your camera to submit an answer.'
          : 'Camera, screen sharing, and fullscreen must stay active.'
      )
      return
    }

    setIsSubmitting(true)
    setShowTranscriptReview(false)
    setTranscript('')
    setAnswer('')

    try {
      console.info('interview_answer_submit_start', {
        sessionId: session.session_id,
        phase: currentPhase,
        answerChars: text.length,
        proctoringReady,
        isMock,
      })
      const data = await onSubmitAnswer(session.session_id, text)
      const isComplete = Boolean(data.interview_complete)
      const nextQuestion = isComplete ? '' : (data.next_question || '')

      console.info('interview_answer_submit_complete', {
        sessionId: session.session_id,
        previousPhase: currentPhase,
        nextPhase: data.phase || currentPhase,
        isComplete,
        status: data.status,
        hasNextQuestion: Boolean(nextQuestion),
        sessionTurn: data.session_turn,
        isMock,
      })

      setCurrentPhase(data.phase || currentPhase)
      setCurrentPhaseGoal(data.phase_goal || currentPhaseGoal)

      if (Array.isArray(data.messages)) {
        // Full messages array returned (real interview + fixed mock)
        setConversation(conversationFromMessages({ ...session, messages: data.messages }))
      } else {
        // Fallback: locally append answer + next question to conversation
        setConversation(prev => [
          ...prev,
          { type: 'answer', content: text, key: `local-answer-${Date.now()}` },
          ...(nextQuestion ? [{ type: 'question', content: nextQuestion, key: `local-q-${Date.now()}` }] : []),
        ])
      }

      if (isComplete) {
        setCurrentQuestion('')
        setCompletedConversation(
          Array.isArray(data.messages)
            ? conversationFromMessages({ ...session, messages: data.messages })
            : [...conversation, { type: 'answer', content: text, key: 'final-answer' }]
        )
        setCompletedDuration(sessionDuration)
        setCompletedSession({
          ...session,
          ...data,
          id: data.db_id || session.db_id || session.id,
          status: data.status || (isMock ? 'completed' : 'analyzing'),
        })
        toast.success('Interview complete!')
      } else {
        if (nextQuestion) {
          setCurrentQuestion(nextQuestion)
          setQuestionCount(count => count + 1)
        }
        setInputMode('voice')
        toast.success('Answer recorded.')
      }
    } catch (err) {
      console.error('Submit answer failed:', err)
      toast.error(err.response?.data?.detail || 'Failed to submit answer')
      setAnswer(text)
    } finally {
      setIsSubmitting(false)
    }
  }, [conversation, currentPhase, currentPhaseGoal, isMock, isSubmitting, onSubmitAnswer, proctoringReady, session, sessionDuration])

  const handleAcceptTranscript = () => {
    submitAnswerText(transcript)
  }

  const handleEditTranscript = (e) => {
    setTranscript(e.target.value)
  }

  const handleCancelTranscript = () => {
    transcriptionGenerationRef.current += 1
    setTranscript('')
    setShowTranscriptReview(false)
    setInputMode('voice')
    clearRecording()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    submitAnswerText(answer)
  }

  const personalizationContext = parseSessionContext(session.personalization_context)

  const handleConfirmEnd = async () => {
    setIsProcessingEnd(true)
    try {
      stopCamera()
      stopScreenShare()
      if (onCompleteSession) {
        const data = await onCompleteSession(session.session_id)
        setCompletedConversation(conversation)
        setCompletedDuration(sessionDuration)
        setCompletedSession({
          ...session,
          ...data,
          id: data.db_id || session.db_id || session.id,
          status: data.status || (isMock ? 'completed' : 'analyzing'),
        })
        toast.success('Interview complete!')
      } else {
        onEnd()
      }
    } catch (err) {
      console.error('Failed to complete session:', err)
      toast.error('Failed to finalize interview')
      onEnd()
    } finally {
      setIsProcessingEnd(false)
      setShowEndModal(false)
    }
  }

  if (completedSession) {
    if (isMock) {
      return (
        <MockInterviewSummary
          session={completedSession}
          conversation={completedConversation}
          sessionDuration={completedDuration}
          onRestart={() => window.location.reload()}
        />
      )
    }
    return (
      <InterviewSummary
        session={completedSession}
        onRestart={() => window.location.reload()}
      />
    )
  }

  const totalQs = session.total_questions || 10
  const progressPercent = Math.min(100, Math.max(0, Math.round(((questionCount - 1) / totalQs) * 100)))

  return (
    <div className="flex flex-col h-full w-full bg-gray-50 text-gray-900 relative">
      {/* ── Overlays & Modals ──────────────────────────────────────────────────────── */}
      {!proctoringReady && (
        <div className="absolute inset-0 z-50 bg-gray-950/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-white border border-gray-200 rounded-xl shadow-xl p-6">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                <Shield className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{isMock ? 'Camera Setup Required' : 'Proctoring setup required'}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {isMock 
                    ? 'Please enable your camera to continue with the mock interview.'
                    : 'Camera, full-screen screen sharing, and browser fullscreen must stay active for the interview.'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5">
              <div className={`p-3 rounded-lg border ${cameraStatus === 'active' ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                  <Camera className="w-4 h-4" />
                  Camera visible
                </div>
                <p className="text-xs text-gray-500 mt-1">{cameraStatus === 'active' ? 'Active' : 'Required before answering'}</p>
              </div>
              
              {!isMock && (
                <>
                  <div className={`p-3 rounded-lg border ${screenShareStatus === 'active' && isEntireScreenShared ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                      <Monitor className="w-4 h-4" />
                      Screen sharing
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {screenShareStatus === 'active'
                        ? isEntireScreenShared ? 'Entire screen active' : 'Select your entire screen, not a tab or window'
                        : 'Required before answering'}
                    </p>
                  </div>
                  <div className={`p-3 rounded-lg border ${isFullscreen ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                      <ArrowRight className="w-4 h-4" />
                      Browser fullscreen
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{isFullscreen ? 'Active' : 'Required before answering'}</p>
                  </div>
                  <div className="p-3 rounded-lg border bg-gray-50 border-gray-200">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                      <AlertTriangle className="w-4 h-4" />
                      Tab switching
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{violations.length ? `${violations.length} event(s) recorded` : 'Do not leave this screen'}</p>
                  </div>
                </>
              )}
            </div>

            {proctoringError && (
              <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
                {proctoringError}
              </p>
            )}
            {!isMock && isMobile && (
              <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
                Screen sharing is not available on most mobile browsers. Use a desktop browser for proctored interviews.
              </p>
            )}
            {!isMock && screenShareSurface && screenShareSurface !== 'monitor' && (
              <p className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-3">
                You selected a {screenShareSurface}. Please share your entire screen.
              </p>
            )}

            <div className="flex flex-wrap gap-2 mt-5">
              <button
                onClick={handleStartProctoring}
                disabled={cameraStatus === 'requesting' || (!isMock && screenShareStatus === 'requesting') || (!isMock && isMobile)}
                className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-bold px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
              >
                {(cameraStatus === 'requesting' || (!isMock && screenShareStatus === 'requesting')) && <Loader2 className="w-4 h-4 animate-spin" />}
                {isMock ? 'Enable Camera' : 'Start Proctored Setup'}
              </button>
              <button
                onClick={onEnd}
                className="inline-flex items-center gap-2 bg-gray-100 text-gray-600 text-sm font-bold px-5 py-3 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {showEndModal && (
        <div className="absolute inset-0 z-[100] bg-gray-950/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-white border border-gray-200 rounded-xl shadow-xl p-6 text-center">
            {isProcessingEnd ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">Processing Final Report...</h3>
                <p className="text-sm text-gray-500">Please wait while we finalize your interview evaluation.</p>
              </div>
            ) : (
              <>
                <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">End Interview Early?</h3>
                <p className="text-sm text-gray-500 mt-2 mb-6">
                  Are you sure you want to end this interview now? Your current progress will be submitted and evaluated to generate your final summary.
                </p>
                <div className="flex justify-center gap-3">
                  <button onClick={() => setShowEndModal(false)} className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-bold hover:bg-gray-200 transition-colors">
                    Cancel
                  </button>
                  <button onClick={handleConfirmEnd} className="px-5 py-2.5 bg-red-600 text-white rounded-lg text-sm font-bold hover:bg-red-700 transition-colors shadow-sm">
                    End Interview
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── TOP SECTION: Unified Question Header ────────────────────────────────────── */}
      <header className="shrink-0 bg-white border-b border-gray-200 shadow-sm z-10 px-4 py-6 sm:px-8 sm:py-8 min-h-[100px] flex flex-col justify-center">
        <div className="max-w-7xl mx-auto w-full flex flex-col gap-4">
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex-1 max-w-md w-full">
              <div className="flex items-center justify-between text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">
                <span>Question {questionCount} of {totalQs}</span>
                <span>{progressPercent}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden border border-gray-200">
                <div className="bg-blue-600 h-full transition-all duration-500 ease-out" style={{ width: `${progressPercent}%` }} />
              </div>
            </div>
            
            <div className="flex items-center gap-2 shrink-0">
              <span className="bg-blue-50 border border-blue-200 text-blue-700 text-[10px] sm:text-xs font-bold px-2.5 py-1 rounded-md uppercase tracking-wider">
                Phase: {currentPhase}
              </span>
              <span className="bg-gray-100 border border-gray-200 text-gray-600 text-[10px] sm:text-xs font-bold px-2.5 py-1 rounded-md uppercase tracking-wider">
                {session.role}
              </span>
              {isMock && (
                <span className="bg-purple-50 border border-purple-200 text-purple-700 text-[10px] sm:text-xs font-bold px-2.5 py-1 rounded-md uppercase tracking-wider">
                  Practice Mode
                </span>
              )}
            </div>
          </div>
          
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-gray-900 leading-snug mt-2 tracking-tight">
            {currentQuestion || session.session_intro}
          </h1>
        </div>
      </header>

      {/* ── MAIN WORKSPACE: 3fr:1fr Layout ───────────────────────────────────────────── */}
      <main className="flex-1 min-h-0 overflow-y-auto w-full p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto w-full h-full flex flex-col lg:grid lg:grid-cols-[3fr_1fr] gap-6 items-start pb-24">
          
          {/* LEFT: Primary Transcript / Answer Area */}
          <div className="w-full flex flex-col gap-4 min-h-[300px] sm:min-h-[400px] lg:min-h-[500px]">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden min-h-[400px]">
              
              <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/80">
                <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2 uppercase tracking-wider">
                  <Edit3 className="w-4 h-4 text-gray-500" />
                  Live Answer Transcript
                </h3>
                {isRecording && (
                  <span className="flex items-center gap-2 text-xs font-bold text-red-600 uppercase tracking-wider animate-pulse">
                    <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
                    Listening...
                  </span>
                )}
                {isTranscribing && (
                  <span className="flex items-center gap-2 text-xs font-bold text-blue-600 uppercase tracking-wider animate-pulse">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Processing...
                  </span>
                )}
              </div>
              
              {/* Transcript Body: Auto-grows naturally */}
              <div className="p-5 bg-white flex flex-col gap-4 flex-grow">
                {conversation.filter(i => i.type === 'answer').length === 0 ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-8 py-12">
                    {isRecording ? (
                      <>
                        <div className="w-16 h-16 rounded-full bg-red-50 border-2 border-red-200 flex items-center justify-center mb-4 shadow-inner">
                          <span className="w-5 h-5 rounded-full bg-red-600 animate-ping" />
                        </div>
                        <h3 className="text-lg font-bold text-red-700 mb-1">🎤 Recording…</h3>
                        <p className="text-sm text-gray-500 max-w-sm">Speak clearly. Your voice is being captured. Click Stop when done.</p>
                      </>
                    ) : isTranscribing ? (
                      <>
                        <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mb-4 shadow-inner">
                          <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
                        </div>
                        <h3 className="text-lg font-bold text-blue-700 mb-1">Transcribing…</h3>
                        <p className="text-sm text-gray-500 max-w-sm">Converting your speech to text. Please wait.</p>
                      </>
                    ) : (
                      <>
                        <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mb-5 shadow-inner">
                          <Mic className="w-8 h-8 text-blue-400" />
                        </div>
                        <h3 className="text-lg font-bold text-gray-700 mb-2">Ready for your answer</h3>
                        <p className="text-sm text-gray-500 font-medium max-w-sm">
                          Click <strong className="text-blue-600">🎤 Record</strong> in the bar below to answer by voice, or type directly in the text box.
                        </p>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4 pb-4">
                    {conversation.filter(i => i.type === 'answer').map((item, idx) => (
                      <div key={item.key || idx} className="p-5 rounded-xl border bg-gray-50 border-gray-200 shadow-sm">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2 flex items-center gap-1.5">
                          <Check className="w-3 h-3 text-green-500" /> Your Answer
                        </p>
                        <p className="text-gray-800 text-sm whitespace-pre-wrap leading-relaxed">{item.content}</p>
                      </div>
                    ))}
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Workspace */}
              <div className="p-4 border-t border-gray-100 bg-gray-50/80">
                {showTranscriptReview ? (
                  <div className="animate-in fade-in slide-in-from-bottom-2">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-purple-600">Review Recognized Speech</span>
                      <button onClick={handleCancelTranscript} className="text-[10px] font-bold uppercase tracking-wider text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1 bg-white border border-gray-200 px-2.5 py-1.5 rounded-md shadow-sm">
                        <X className="w-3 h-3" /> Discard
                      </button>
                    </div>
                    <textarea
                      value={transcript}
                      onChange={handleEditTranscript}
                      disabled={!proctoringReady}
                      rows={5}
                      className="w-full p-4 border border-purple-200 bg-white rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent shadow-sm disabled:bg-gray-100 disabled:text-gray-400"
                    />
                    <div className="flex justify-end mt-3">
                      <button
                        onClick={handleAcceptTranscript}
                        disabled={isSubmitting || !transcript.trim() || !proctoringReady}
                        className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-bold px-6 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-all shadow-sm"
                      >
                        {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Submit Answer
                      </button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-3">
                    <textarea
                      value={answer}
                      onChange={e => setAnswer(e.target.value)}
                      placeholder={
                        !proctoringReady
                          ? 'Complete camera setup to answer.'
                          : isRecording
                          ? 'Recording in progress — stop recording to transcribe…'
                          : 'Type your answer here… (or use voice recording below)'
                      }
                      disabled={!proctoringReady || isRecording}
                      rows={4}
                      className="w-full p-4 border border-gray-200 bg-white rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent shadow-sm disabled:bg-gray-100 disabled:text-gray-400 transition-all"
                      onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e) }}
                    />
                    <div className="flex items-center gap-3">
                      <button
                        type="submit"
                        disabled={isSubmitting || !answer.trim() || !proctoringReady}
                        className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg text-sm font-bold hover:bg-blue-700 disabled:opacity-50 transition-all flex justify-center items-center gap-2 shadow-sm"
                      >
                        {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {isSubmitting ? 'Submitting…' : 'Submit Text Answer'}
                      </button>
                      <span className="text-[10px] font-medium text-gray-400 hidden sm:inline-block shrink-0">Ctrl+Enter</span>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Secondary Area (Camera, Metrics, Monitoring) */}
          <div className="w-full flex flex-col gap-4 lg:sticky lg:top-4">
            
            {/* Camera Feed - Top Priority */}
            <div className="bg-gray-950 rounded-xl overflow-hidden border border-gray-800 shadow-xl relative aspect-video min-h-[240px] flex items-center justify-center shrink-0">
              {cameraStatus === 'active' ? (
                <video ref={cameraVideoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
              ) : cameraStatus === 'requesting' ? (
                <div className="text-center text-gray-400">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                  <p className="text-sm font-medium tracking-wide">Requesting camera...</p>
                </div>
              ) : (
                <div className="text-center text-gray-500">
                  <Video className="w-10 h-10 mx-auto mb-3 opacity-50" />
                  <p className="text-xs font-bold uppercase tracking-wider text-gray-400">Camera Offline</p>
                </div>
              )}
              {cameraStatus === 'active' && (
                <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-sm border border-white/10 text-white text-[10px] font-bold uppercase tracking-wider px-2.5 py-1.5 rounded flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]" /> Live Feed
                </div>
              )}
            </div>

            {/* Ultra Compact Metrics Chips */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4 gap-2">
              <div className="bg-white border border-gray-200 rounded-lg p-2.5 text-center shadow-sm">
                <span className="block text-sm font-extrabold text-gray-900">{questionCount}</span>
                <span className="text-[8px] font-bold uppercase tracking-widest text-gray-500 mt-1">Questions</span>
              </div>
              <div className="bg-white border border-gray-200 rounded-lg p-2.5 text-center shadow-sm">
                <span className="block text-sm font-extrabold text-gray-900 tabular-nums">
                  {Math.floor(sessionDuration / 60)}:{String(sessionDuration % 60).padStart(2, '0')}
                </span>
                <span className="text-[8px] font-bold uppercase tracking-widest text-gray-500 mt-1">Time</span>
              </div>
              {!isMock && (
                <div className={`bg-white border ${violations.length > 0 ? 'border-red-200' : 'border-gray-200'} rounded-lg p-2.5 text-center shadow-sm`}>
                  <span className={`block text-sm font-extrabold ${violations.length > 0 ? 'text-red-600' : 'text-gray-900'}`}>{violations.length}/3</span>
                  <span className="text-[8px] font-bold uppercase tracking-widest text-gray-500 mt-1">Alerts</span>
                </div>
              )}
              <div className="bg-white border border-gray-200 rounded-lg p-2.5 text-center shadow-sm">
                <span className="block text-sm font-extrabold text-gray-900">High</span>
                <span className="text-[8px] font-bold uppercase tracking-widest text-gray-500 mt-1">Confidence</span>
              </div>
            </div>

            {/* Conditional Security Alerts Log */}
            {!isMock && violations.length > 0 && (
              <div className="bg-white border border-red-200 rounded-xl p-4 shadow-sm flex flex-col max-h-[220px]">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-red-600 mb-3 flex items-center gap-1.5 shrink-0">
                  <AlertTriangle className="w-3.5 h-3.5" /> Security Alerts
                </h4>
                <div className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
                  {violations.map((v, idx) => (
                    <div key={idx} className="flex gap-2 text-xs border-l-2 border-red-500 pl-2.5 py-1 bg-red-50/50 rounded-r-md">
                      <span className="text-gray-400 font-mono text-[10px] shrink-0 pt-0.5">{new Date(v.timestamp).toLocaleTimeString()}</span>
                      <span className="text-red-700 font-medium">{v.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Conditional Screen Share Preview */}
            {!isMock && screenShareStatus === 'active' && (
              <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-sm flex flex-col">
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-1.5">
                  <Monitor className="w-3.5 h-3.5 text-gray-400" /> Screen Sharing
                </h4>
                <div className="bg-gray-900 rounded-lg overflow-hidden flex items-center justify-center relative aspect-video max-h-[180px] shadow-inner">
                  <video ref={screenVideoRef} autoPlay playsInline muted className="w-full h-full object-contain" />
                </div>
              </div>
            )}

          </div>
        </div>
      </main>

      {/* ── STICKY BOTTOM CONTROL BAR (Max Height 64px) ────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 right-0 bg-gray-950 text-white border-t border-gray-800 px-4 py-2 z-40 shadow-[0_-20px_40px_rgba(0,0,0,0.3)] h-auto sm:h-[64px] flex items-center">
        <div className="max-w-7xl mx-auto flex flex-wrap sm:flex-nowrap items-center justify-between gap-3 w-full">
          
          <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-start">
            {isRecording ? (
              <div className="flex items-center gap-2 bg-red-500/20 text-red-400 px-3 py-1.5 rounded border border-red-500/30">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
                <span className="text-[10px] font-bold uppercase tracking-wider hidden sm:inline-block">Recording</span>
                <span className="text-xs font-mono font-bold ml-1 text-red-300">
                  {Math.floor(duration / 60)}:{String(duration % 60).padStart(2, '0')}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-white/5 text-gray-400 px-3 py-1.5 rounded border border-white/10">
                <Mic className="w-3.5 h-3.5 opacity-50" />
                <span className="text-[10px] font-bold uppercase tracking-wider hidden sm:inline-block">Mic Standby</span>
              </div>
            )}
            
            <div className="flex items-center gap-1.5 text-gray-400 text-xs font-mono font-bold px-2 py-1">
              <Clock className="w-3.5 h-3.5 opacity-50" />
              {Math.floor(sessionDuration / 60)}:{String(sessionDuration % 60).padStart(2, '0')}
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            {isRecording ? (
              <button onClick={handleStopRecording} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 bg-red-600 text-white text-[11px] font-bold uppercase tracking-wider px-4 py-2 rounded hover:bg-red-700 transition-all shadow-[0_0_15px_rgba(220,38,38,0.4)]">
                <StopCircle className="w-3.5 h-3.5" /> Stop
              </button>
            ) : (
              <button onClick={handleStartRecording} disabled={!proctoringReady} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 bg-blue-600 text-white text-[11px] font-bold uppercase tracking-wider px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 transition-all shadow-[0_0_15px_rgba(37,99,235,0.4)]">
                <Mic className="w-3.5 h-3.5" /> Record Voice
              </button>
            )}
            
            <div className="w-px h-6 bg-gray-800 hidden sm:block mx-1" />
            
            <button onClick={() => setShowEndModal(true)} className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 bg-transparent text-gray-400 hover:text-white hover:bg-white/10 text-[11px] font-bold uppercase tracking-wider px-3 py-2 rounded transition-colors border border-transparent hover:border-gray-700">
              End Interview
            </button>
          </div>

        </div>
      </footer>
    </div>
  )
}
