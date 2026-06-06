import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Camera, CameraOff, Monitor, MonitorOff, Mic, MicOff,
  ArrowRight, Edit3, Check, X, Send, AlertTriangle,
  Video, StopCircle, Loader2, Shield,
} from 'lucide-react'
import useRecorder from '../../hooks/useRecorder'
import useInterviewMedia from '../../hooks/useInterviewMedia'
import InterviewStatusCard from './InterviewStatusCard'
import InterviewSummary from './InterviewSummary'
import toast from 'react-hot-toast'

export default function InterviewWorkspaceShell({ session, onEnd, onSubmitAnswer, onTranscribeAudio, onRecordProctoringViolation, onCompleteSession }) {
  const {
    cameraEnabled, cameraStatus, screenShareEnabled, screenShareStatus, screenShareSurface, isMobile,
    cameraVideoRef, screenVideoRef,
    startCamera, stopCamera, startScreenShare, stopScreenShare,
  } = useInterviewMedia()

  const {
    isRecording, duration, audioBlob, error: recorderError,
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
  const [currentPhase, setCurrentPhase] = useState(session.phase || 'Introduction')
  const [currentPhaseGoal, setCurrentPhaseGoal] = useState(session.phase_goal || '')
  const [lastFeedback, setLastFeedback] = useState(null)
  const [avgScore, setAvgScore] = useState(null)
  const [questionCount, setQuestionCount] = useState(1)
  const [sessionDuration, setSessionDuration] = useState(0)
  const [completedSession, setCompletedSession] = useState(null)
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

  useEffect(() => {
    const initialMessages = []
    if (session?.session_intro) {
      initialMessages.push({ type: 'intro', content: session.session_intro })
    }
    if (session?.messages && session.messages.length > 0) {
      session.messages.forEach(msg => {
        if (msg.role === 'ai') {
          initialMessages.push({ type: 'question', content: msg.content })
        } else if (msg.role === 'user') {
          initialMessages.push({ type: 'answer', content: msg.content })
        } else if (msg.role === 'feedback') {
          initialMessages.push({
            type: 'feedback',
            content: msg.content,
            data: { score: msg.score }
          })
        }
      })
    } else if (session?.question) {
      initialMessages.push({ type: 'question', content: session.question })
    }
    setConversation(initialMessages)

    const aiMsgs = session?.messages?.filter(m => m.role === 'ai') || []
    if (aiMsgs.length > 0) {
      const lastAi = aiMsgs[aiMsgs.length - 1]
      setCurrentQuestion(lastAi.content || '')
      setCurrentPhase(lastAi.phase || 'Introduction')
      setQuestionCount(aiMsgs.length)
    } else {
      setCurrentQuestion(session?.question || '')
      setCurrentPhase(session?.phase || 'Introduction')
      setQuestionCount(session?.question ? 1 : 0)
    }
    setCurrentPhaseGoal(session?.phase_goal || '')

    const feedbackScores = session?.messages?.filter(m => m.role === 'feedback' && typeof m.score === 'number').map(m => m.score) || []
    if (feedbackScores.length > 0) {
      const avg = feedbackScores.reduce((a, b) => a + b, 0) / feedbackScores.length
      setAvgScore(avg)
      const lastF = session.messages.filter(m => m.role === 'feedback')
      if (lastF.length > 0) {
        setLastFeedback({
          feedback_message: lastF[lastF.length - 1].content,
          evaluation: { score: lastF[lastF.length - 1].score }
        })
      }
    } else {
      setAvgScore(null)
      setLastFeedback(null)
    }

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
    const doTranscribe = async () => {
      setIsTranscribing(true)
      try {
        const result = await onTranscribeAudio(audioBlob)
        setTranscript(result.transcript)
        setShowTranscriptReview(true)
      } catch (err) {
        console.error('Transcription failed:', err)
        toast.error('Unable to transcribe audio. You can type your answer instead.')
        setInputMode('text')
      } finally {
        setIsTranscribing(false)
        clearRecording()
      }
    }
    doTranscribe()
  }, [audioBlob, clearRecording])

  const addViolation = useCallback(async (type, detail) => {
    const entry = {
      type,
      detail,
      timestamp: new Date().toISOString(),
    }
    violationsRef.current = [...violationsRef.current, entry].slice(-20)
    setViolations(violationsRef.current)

    try {
      const result = await onRecordProctoringViolation(session.session_id, type, detail)
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
  }, [session])

  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement)
      setIsFullscreen(active)
      if (setupCompleted && !active) {
        addViolation('fullscreen_exit', 'Candidate exited fullscreen mode.')
      }
    }
    const handleVisibilityChange = () => {
      if (setupCompleted && document.hidden) {
        addViolation('tab_switch', 'Candidate switched away from the interview tab.')
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [addViolation, setupCompleted])

  useEffect(() => {
    if (setupCompleted && cameraStatus !== 'active') {
      addViolation('camera_off', 'Camera was turned off or became unavailable.')
    }
  }, [addViolation, cameraStatus, setupCompleted])

  useEffect(() => {
    if (setupCompleted && screenShareStatus !== 'active') {
      addViolation('screen_share_off', 'Screen sharing was stopped or became unavailable.')
    }
  }, [addViolation, screenShareStatus, setupCompleted])

  const isEntireScreenShared = !screenShareSurface || screenShareSurface === 'monitor'
  const proctoringReady = (
    proctoringStarted &&
    cameraStatus === 'active' &&
    screenShareStatus === 'active' &&
    isFullscreen &&
    isEntireScreenShared
  )

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
    } catch (err) {
      setIsFullscreen(false)
      return false
    }
  }, [])

  const handleStartProctoring = async () => {
    setProctoringError('')
    if (screenShareEnabled && !isEntireScreenShared) {
      stopScreenShare()
      setProctoringError('Please start again and choose your entire screen, not a browser tab or window.')
      return
    }
    setProctoringStarted(true)
    const screenPromise = startScreenShare()
    const cameraPromise = startCamera()
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
      toast.error('Camera, screen sharing, and fullscreen must stay active.')
      return
    }

    setIsSubmitting(true)
    setShowTranscriptReview(false)
    setTranscript('')
    setAnswer('')
    setConversation(prev => [...prev, { type: 'answer', content: text }])

    try {
      const data = await onSubmitAnswer(session.session_id, text)
      const nextQuestion = data.next_question || ''
      const isComplete = Boolean(data.interview_complete)
      const finalFeedbackText = typeof data.final_feedback === 'string'
        ? data.final_feedback
        : data.final_feedback
          ? [
              data.final_feedback.verdict,
              data.final_feedback.verdict_explanation,
              ...(data.final_feedback.improvement_plan || []),
            ].filter(Boolean).join('\n')
          : ''

      setLastFeedback(data)
      setAvgScore(data.avg_score)
      setCurrentPhase(data.phase || currentPhase)
      setCurrentPhaseGoal(data.phase_goal || currentPhaseGoal)

      if (nextQuestion) {
        setCurrentQuestion(nextQuestion)
      }

      setConversation(prev => {
        const nextItems = [
          ...prev,
          {
            type: 'feedback',
            content: data.feedback_message || data.feedback || 'Answer evaluated.',
            data: { score: data.evaluation?.score },
          },
        ]

        if (isComplete) {
          nextItems.push({
            type: 'feedback',
            content: finalFeedbackText || data.verdict_explanation || 'Interview complete.',
            data: { score: data.avg_score },
          })
        } else if (nextQuestion) {
          nextItems.push({ type: 'question', content: nextQuestion })
        }

        return nextItems
      })

      if (isComplete) {
        setCompletedSession({
          ...session,
          ...data,
          id: data.db_id || session.db_id || session.id,
          avg_score: data.avg_score ?? data.evaluation?.score ?? avgScore ?? 0,
          final_feedback: finalFeedbackText || data.feedback_message || '',
          final_verdict: data.final_verdict || data.evaluation?.final_verdict || '',
        })
        toast.success('Interview complete!')
      } else {
        if (nextQuestion) {
          setQuestionCount(count => count + 1)
        }
        setInputMode('voice')
        toast.success('Answer evaluated!')
      }
    } catch (err) {
      console.error('Submit answer failed:', err)
      toast.error(err.response?.data?.detail || 'Failed to submit answer')
      setAnswer(text)
    } finally {
      setIsSubmitting(false)
    }
  }, [avgScore, currentPhase, currentPhaseGoal, isSubmitting, proctoringReady, session])

  const handleAcceptTranscript = () => {
    submitAnswerText(transcript)
  }

  const handleEditTranscript = (e) => {
    setTranscript(e.target.value)
  }

  const handleCancelTranscript = () => {
    setTranscript('')
    setShowTranscriptReview(false)
    setInputMode('voice')
    clearRecording()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    submitAnswerText(answer)
  }

  const statusForCard = (status) => {
    if (status === 'active') return 'active'
    if (status === 'denied' || status === 'unavailable' || status === 'error') return 'denied'
    return 'idle'
  }

  const handleConfirmEnd = async () => {
    setIsProcessingEnd(true)
    try {
      stopCamera()
      stopScreenShare()
      if (onCompleteSession) {
        const data = await onCompleteSession(session.session_id)
        setCompletedSession({
          ...session,
          ...data,
          id: data.db_id || session.db_id || session.id,
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
    return (
      <InterviewSummary
        session={completedSession}
        onRestart={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="h-screen flex flex-col gap-3 p-3 relative overflow-hidden">
      {!proctoringReady && (
        <div className="absolute inset-0 z-50 bg-gray-950/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-white border border-gray-200 rounded-xl shadow-xl p-6">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                <Shield className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Proctoring setup required</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Camera, full-screen screen sharing, and browser fullscreen must stay active for the interview.
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
            </div>

            {proctoringError && (
              <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
                {proctoringError}
              </p>
            )}
            {isMobile && (
              <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
                Screen sharing is not available on most mobile browsers. Use a desktop browser for proctored interviews.
              </p>
            )}
            {screenShareSurface && screenShareSurface !== 'monitor' && (
              <p className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-3">
                You selected a {screenShareSurface}. Please share your entire screen.
              </p>
            )}

            <div className="flex flex-wrap gap-2 mt-5">
              <button
                onClick={handleStartProctoring}
                disabled={cameraStatus === 'requesting' || screenShareStatus === 'requesting' || isMobile}
                className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm px-5 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {(cameraStatus === 'requesting' || screenShareStatus === 'requesting') && <Loader2 className="w-4 h-4 animate-spin" />}
                Start Proctored Interview
              </button>
              <button
                onClick={onEnd}
                className="inline-flex items-center gap-2 bg-gray-100 text-gray-600 text-sm px-4 py-2.5 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between px-1">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{session.role} Interview</h2>
          <p className="text-sm text-gray-500">
            Phase: {currentPhase} {avgScore !== null && `| Avg Score: ${avgScore.toFixed(1)}/10`} | Proctoring: {proctoringReady ? 'Active' : 'Required'}
          </p>
        </div>
        <button onClick={() => setShowEndModal(true)} className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors border border-red-200 shadow-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> End Interview
        </button>
      </div>

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
                  <button onClick={() => setShowEndModal(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-200 transition-colors">
                    Cancel
                  </button>
                  <button onClick={handleConfirmEnd} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 transition-colors">
                    End Interview
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* stepper progress tracker at top */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Interview Progression</h3>
        <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1 text-[11px] font-medium text-gray-400 scrollbar-thin">
          {["Introduction", "Resume Deep Dive", "Core Technical Round", "Problem Solving", "Behavioral Round", "Pressure / Cross-questioning", "Candidate Questions", "Final Evaluation"].map((p, idx, arr) => {
            const isCurrent = currentPhase === p;
            const isPast = arr.indexOf(currentPhase) > idx;
            return (
              <div key={p} className="flex items-center gap-1.5 shrink-0">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  isCurrent ? 'bg-blue-600 text-white font-bold animate-pulse' :
                  isPast ? 'bg-green-100 text-green-700 border border-green-200' :
                  'bg-gray-100 text-gray-400 border border-gray-200'
                }`}>
                  {isPast ? '✓' : idx + 1}
                </span>
                <span className={isCurrent ? 'text-blue-700 font-semibold' : isPast ? 'text-gray-700' : 'text-gray-400'}>
                  {p}
                </span>
                {idx < arr.length - 1 && <span className="text-gray-300 mx-1">→</span>}
              </div>
            )
          })}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-3 min-h-0 overflow-hidden">
        {/* LEFT COLUMN — AI Interviewer Message Log */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-3 min-h-0">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex-1 flex flex-col min-h-0">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Interviewer</h3>
                <p className="text-sm font-medium text-gray-700 capitalize">
                  {session.interviewer_persona || 'Balanced'} Persona (Phase: {currentPhase})
                </p>
              </div>
              {session.personalization_context && JSON.parse(session.personalization_context || '{}').verification_active && (
                <span className="bg-amber-100 border border-amber-200 text-amber-800 text-[10px] px-2.5 py-1 rounded-full animate-pulse font-semibold">
                  Claim Verification: {JSON.parse(session.personalization_context || '{}').current_verification_claim}
                </span>
              )}
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {conversation.length === 0 && (
                <p className="text-sm text-blue-700 bg-blue-50 rounded-lg p-3">
                  {currentQuestion || session.session_intro}
                </p>
              )}
              {conversation.map((item, i) => (
                <div key={i} className={`text-sm p-3 rounded-lg ${
                  item.type === 'question' ? 'bg-blue-50 border border-blue-100' :
                  item.type === 'answer' ? 'bg-gray-50 border border-gray-200 ml-4' :
                  item.type === 'feedback' ? 'bg-green-50 border border-green-100' :
                  'bg-yellow-50 border border-yellow-100'
                }`}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
                    {item.type === 'question' && 'Question'}
                    {item.type === 'answer' && 'Your Answer'}
                    {item.type === 'feedback' && 'Feedback'}
                    {item.type === 'intro' && 'Session Intro'}
                  </p>
                  <p className="text-gray-800 whitespace-pre-wrap">{item.content}</p>
                  {item.data?.score !== undefined && (
                    <p className="mt-1 text-sm font-medium text-green-700">Score: {item.data.score}/10</p>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN — Candidate Camera Preview & Proctoring Indicators */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-3 min-h-0 overflow-y-auto pr-1">
          {/* Webcam Live Stream Panel */}
          <div className="bg-gray-950 rounded-xl border border-gray-800 shadow-sm overflow-hidden flex flex-col shrink-0">
            <div className="relative aspect-video bg-gray-900 flex items-center justify-center">
              {cameraStatus === 'active' ? (
                <>
                  <video ref={cameraVideoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                  <div className="absolute bottom-3 left-3 bg-black/60 text-white text-xs px-2 py-1 rounded-md flex items-center gap-1.5">
                    <Camera className="w-3 h-3 text-green-400" />
                    Feed Active
                  </div>
                </>
              ) : cameraStatus === 'requesting' ? (
                <div className="text-center text-gray-400">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                  <p className="text-sm">Requesting camera...</p>
                </div>
              ) : (
                <div className="text-center text-gray-500 p-6">
                  <Video className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-sm font-medium mb-1">Camera Stream Required</p>
                  <button
                    onClick={startCamera}
                    className="inline-flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs px-3 py-1.5 rounded-lg transition-colors"
                  >
                    Enable Camera
                  </button>
                </div>
              )}
              
              {/* Overlay Indicators */}
              <div className="absolute top-3 left-3 flex flex-col gap-1.5 pointer-events-none">
                <div className={`text-[10px] font-semibold px-2 py-1 rounded-md shadow-md flex items-center gap-1.5 ${
                  isRecording ? 'bg-red-500/90 text-white' : 'bg-gray-800/80 text-gray-300'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full bg-current ${isRecording ? 'animate-ping' : ''}`} />
                  {isRecording ? 'Recording ●' : 'Idle'}
                </div>
                <div className={`text-[10px] font-semibold px-2 py-1 rounded-md shadow-md flex items-center gap-1 ${
                  micStatus === 'active' ? 'bg-green-600/90 text-white' : 'bg-gray-800/80 text-gray-300'
                }`}>
                  {micStatus === 'active' ? 'Mic Active ✓' : 'Mic Off ✕'}
                </div>
                <div className={`text-[10px] font-semibold px-2 py-1 rounded-md shadow-md flex items-center gap-1 ${
                  cameraStatus === 'active' ? 'bg-green-600/90 text-white' : 'bg-red-600/95 text-white'
                }`}>
                  {cameraStatus === 'active' ? 'Face Detected ✓' : 'Face Not Detected ✕'}
                </div>
                <div className={`text-[10px] font-semibold px-2 py-1 rounded-md shadow-md flex items-center gap-1 ${
                  proctoringReady ? 'bg-blue-600/95 text-white' : 'bg-amber-600/90 text-white animate-pulse'
                }`}>
                  {proctoringReady ? 'Proctoring Active ✓' : 'Proctoring Inactive ✕'}
                </div>
              </div>
            </div>
          </div>

          {/* Screen Share Preview Panel */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-3 shrink-0 flex flex-col">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Screen Share Status</h4>
            <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center overflow-hidden">
              {screenShareStatus === 'active' ? (
                <video ref={screenVideoRef} autoPlay playsInline muted className="w-full h-full object-contain" />
              ) : (
                <div className="text-center text-gray-500 p-4">
                  <Monitor className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  <button onClick={startScreenShare} className="text-xs text-blue-600 font-semibold hover:underline">
                    Share Screen
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Security Violations Log Panel */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex-1 flex flex-col min-h-[140px]">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Security Alerts ({violations.length}/3)</h4>
            <div className="flex-1 overflow-y-auto space-y-2 max-h-[160px] scrollbar-thin">
              {violations.length === 0 ? (
                <p className="text-xs text-gray-400">No alerts triggered. Keep window fullscreen and tab active.</p>
              ) : (
                violations.map((v, idx) => (
                  <div key={idx} className="flex gap-2 text-xs border-l-2 border-red-500 pl-2 py-0.5 bg-red-50/50">
                    <span className="text-gray-400 font-mono text-[10px]">{new Date(v.timestamp).toLocaleTimeString()}</span>
                    <span className="text-red-700 font-medium">{v.detail}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Metrics summary card */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-3 shrink-0">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Session Metrics</h4>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                <span className="block text-lg font-bold text-gray-700">{questionCount}</span>
                <span className="text-[10px] text-gray-400">Questions</span>
              </div>
              <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                <span className="block text-lg font-bold text-gray-700 tabular-nums">
                  {Math.floor(sessionDuration / 60)}:{String(sessionDuration % 60).padStart(2, '0')}
                </span>
                <span className="text-[10px] text-gray-400">Time elapsed</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM PANEL — Input and audio transcription */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 shrink-0">
        {isTranscribing ? (
          <div className="flex items-center gap-2 text-gray-500 py-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <span className="text-sm font-medium">Transcribing audio answer...</span>
          </div>
        ) : showTranscriptReview ? (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Edit3 className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-semibold text-purple-700">Review Speech Transcript</span>
            </div>
            <textarea
              value={transcript}
              onChange={handleEditTranscript}
              disabled={!proctoringReady}
              rows={3}
              className="w-full p-3 border border-purple-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-300 disabled:bg-gray-100 disabled:text-gray-400"
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={handleAcceptTranscript}
                disabled={isSubmitting || !transcript.trim() || !proctoringReady}
                className="inline-flex items-center gap-1.5 bg-purple-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Use & Submit
              </button>
              <button onClick={handleCancelTranscript} className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-600 text-sm px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors">
                <X className="w-4 h-4" />
                Re-record
              </button>
            </div>
          </div>
        ) : isRecording ? (
          <div className="flex items-center justify-between py-1 bg-red-50 border border-red-100 rounded-lg px-3 animate-pulse">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 bg-red-600 rounded-full animate-ping" />
              <span className="text-red-700 font-semibold text-sm">Recording Speech...</span>
              <span className="text-red-600 font-mono text-sm tabular-nums">
                {Math.floor(duration / 60)}:{String(duration % 60).padStart(2, '0')}
              </span>
            </div>
            <button onClick={handleStopRecording} className="inline-flex items-center gap-1.5 bg-gray-800 text-white text-xs px-3.5 py-1.5 rounded-lg hover:bg-gray-900 transition-colors">
              <StopCircle className="w-3.5 h-3.5 text-red-500" />
              Stop Recording
            </button>
          </div>
        ) : inputMode === 'voice' ? (
          <div className="flex items-center gap-2 py-1">
            <button onClick={handleStartRecording} className="inline-flex items-center gap-2 bg-red-600 text-white text-sm px-5 py-2.5 rounded-lg hover:bg-red-700 transition-colors font-medium">
              <Mic className="w-4 h-4" />
              Start Voice Recording
            </button>
            <button onClick={() => setInputMode('text')} className="inline-flex items-center gap-1.5 text-gray-500 text-sm px-4 py-2.5 rounded-lg hover:bg-gray-100 transition-colors">
              <Edit3 className="w-4 h-4" />
              Type Answer Instead
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              placeholder={proctoringReady ? "Type your answer here..." : "Proctoring setup inactive. Reactivate camera/screenshare/fullscreen to answer."}
              disabled={!proctoringReady}
              rows={2}
              className="flex-1 p-3 border border-gray-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:bg-gray-100 disabled:text-gray-400"
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e) }}
            />
            <div className="flex flex-col gap-1">
              <button type="submit" disabled={isSubmitting || !answer.trim() || !proctoringReady} className="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex-1 flex items-center gap-1.5 font-medium">
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Submit Answer
              </button>
            </div>
          </form>
        )}
        <div className="flex items-center justify-between mt-2 text-[11px] text-gray-400">
          <p>
            {showTranscriptReview
              ? 'Review and edit transcript, then submit.'
              : isRecording
              ? 'Click Stop to process your speech.'
              : inputMode === 'voice'
              ? 'Use voice for a realistic experience. Press start and talk.'
              : 'Press Ctrl+Enter or Cmd+Enter to submit.'}
          </p>
          {inputMode === 'text' && !isRecording && !showTranscriptReview && (
            <button
              onClick={() => setInputMode('voice')}
              className="text-[11px] text-blue-500 hover:underline hover:text-blue-700"
            >
              Switch back to Voice
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
