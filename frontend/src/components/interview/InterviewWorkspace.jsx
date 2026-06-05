import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Camera, CameraOff, Monitor, MonitorOff, Mic, MicOff,
  ArrowRight, Edit3, Check, X, Send, AlertTriangle,
  Video, StopCircle, Loader2, Shield,
} from 'lucide-react'
import useRecorder from '../../hooks/useRecorder'
import useInterviewMedia from '../../hooks/useInterviewMedia'
import { submitAnswer, transcribeAudio } from '../../api/interview'
import InterviewStatusCard from './InterviewStatusCard'
import InterviewSummary from './InterviewSummary'
import toast from 'react-hot-toast'

export default function InterviewWorkspace({ session, onEnd }) {
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
  const [proctoringError, setProctoringError] = useState('')
  const [violations, setViolations] = useState([])

  const messagesEndRef = useRef(null)
  const durationTimerRef = useRef(null)
  const violationsRef = useRef([])

  useEffect(() => {
    const initialMessages = []
    if (session?.session_intro) {
      initialMessages.push({ type: 'intro', content: session.session_intro })
    }
    if (session?.question) {
      initialMessages.push({ type: 'question', content: session.question })
    }
    setConversation(initialMessages)
    setCurrentQuestion(session?.question || '')
    setCurrentPhase(session?.phase || 'Introduction')
    setCurrentPhaseGoal(session?.phase_goal || '')
    setQuestionCount(session?.question ? 1 : 0)
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
        const result = await transcribeAudio(audioBlob)
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

  const addViolation = useCallback((type, detail) => {
    const entry = {
      type,
      detail,
      timestamp: new Date().toISOString(),
    }
    violationsRef.current = [...violationsRef.current, entry].slice(-20)
    setViolations(violationsRef.current)
  }, [])

  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement)
      setIsFullscreen(active)
      if (proctoringStarted && !active) {
        addViolation('fullscreen_exit', 'Candidate exited fullscreen mode.')
      }
    }
    const handleVisibilityChange = () => {
      if (proctoringStarted && document.hidden) {
        addViolation('tab_switch', 'Candidate switched away from the interview tab.')
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [addViolation, proctoringStarted])

  useEffect(() => {
    if (proctoringStarted && cameraStatus !== 'active' && cameraStatus !== 'requesting') {
      addViolation('camera_off', 'Camera was turned off or became unavailable.')
    }
  }, [addViolation, cameraStatus, proctoringStarted])

  useEffect(() => {
    if (proctoringStarted && screenShareStatus !== 'active' && screenShareStatus !== 'requesting') {
      addViolation('screen_share_off', 'Screen sharing was stopped or became unavailable.')
    }
  }, [addViolation, proctoringStarted, screenShareStatus])

  const isEntireScreenShared = !screenShareSurface || screenShareSurface === 'monitor'
  const proctoringReady = (
    proctoringStarted &&
    cameraStatus === 'active' &&
    screenShareStatus === 'active' &&
    isFullscreen &&
    isEntireScreenShared
  )

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
      const data = await submitAnswer(session.session_id, text)
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
        <button onClick={onEnd} className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
          End Interview
        </button>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-3 min-h-0">
        {/* LEFT PANEL — Question + Feedback */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-3 min-h-0">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex-1 flex flex-col min-h-0">
            <div className="p-4 border-b border-gray-100">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Interviewer</h3>
              <p className="text-sm font-medium text-gray-700 capitalize">{session.interviewer_persona || 'Balanced'} Persona</p>
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

          <InterviewStatusCard
            questionCount={questionCount}
            duration={sessionDuration}
            micStatus={statusForCard(micStatus)}
            cameraStatus={statusForCard(cameraStatus)}
            screenShareStatus={statusForCard(screenShareStatus)}
          />
        </div>

        {/* CENTER PANEL — Camera Preview */}
        <div className="col-span-12 lg:col-span-5 flex flex-col gap-3 min-h-0">
          <div className="bg-gray-900 rounded-xl border border-gray-700 shadow-sm flex-1 relative overflow-hidden flex items-center justify-center">
            {cameraStatus === 'active' ? (
              <>
                <video ref={cameraVideoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                <div className="absolute bottom-3 left-3 bg-black/60 text-white text-xs px-2 py-1 rounded-md flex items-center gap-1.5">
                  <Camera className="w-3 h-3" />
                  Camera Active
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
                <p className="text-sm font-medium mb-1">Camera Preview</p>
                <p className="text-xs opacity-70 mb-3">Local preview only. Not recorded or analyzed.</p>
                <button
                  onClick={startCamera}
                  className="inline-flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-sm px-4 py-2 rounded-lg transition-colors"
                >
                  <Camera className="w-4 h-4" />
                  Enable Camera
                </button>
              </div>
            )}
            <div className="absolute bottom-3 right-3 bg-black/60 text-white text-xs px-2 py-1 rounded-md flex items-center gap-1">
              <Shield className="w-3 h-3 text-green-400" />
              Local Only
            </div>
          </div>

          {lastFeedback && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Latest Feedback</h4>
              <p className="text-sm text-gray-700">
                Score: <span className="font-semibold text-green-600">{lastFeedback.evaluation?.score}/10</span>
                {' '}- {lastFeedback.evaluation?.final_verdict}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {lastFeedback.evaluation?.verdict_explanation}
              </p>
              {lastFeedback.answer_expectation && (
                <p className="text-xs text-gray-500 mt-2">
                  Expected answer shape: {lastFeedback.answer_expectation}
                </p>
              )}
            </div>
          )}

          <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 flex items-start gap-2">
            <Shield className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
            <p className="text-xs text-blue-700">
              Camera preview is local only. Video is not recorded, stored, streamed, or analyzed.
              Screen sharing and browser fullscreen are required while the interview is active.
            </p>
          </div>
        </div>

        {/* RIGHT PANEL — Screen Share Preview */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-3 min-h-0">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex-1 flex flex-col">
            <div className="p-3 border-b border-gray-100">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Screen Share</h3>
            </div>
            <div className="flex-1 flex items-center justify-center p-4">
              {isMobile ? (
                <div className="text-center text-gray-400">
                  <MonitorOff className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Screen sharing unavailable on this device.</p>
                </div>
              ) : screenShareStatus === 'active' ? (
                <div className="w-full h-full relative">
                  <video ref={screenVideoRef} autoPlay playsInline muted className="w-full h-full object-contain rounded-lg bg-gray-900" />
                  <button
                    onClick={stopScreenShare}
                    className="absolute top-2 right-2 bg-red-600 text-white text-xs px-3 py-1.5 rounded-md hover:bg-red-700 transition-colors"
                  >
                    Stop Sharing
                  </button>
                  <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded-md flex items-center gap-1">
                    <Monitor className="w-3 h-3" />
                    Sharing
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  {screenShareStatus === 'denied' && (
                    <p className="text-sm text-red-500 mb-2">Screen share permission denied.</p>
                  )}
                  <button
                    onClick={startScreenShare}
                    className="inline-flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <Monitor className="w-4 h-4" />
                    Share Screen
                  </button>
                  <p className="text-xs text-gray-400 mt-2">Required for proctoring.</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Controls</h4>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={cameraEnabled ? stopCamera : startCamera}
                className={`inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border transition-colors ${
                  cameraEnabled
                    ? 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100'
                    : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
                }`}
              >
                {cameraEnabled ? <Camera className="w-3 h-3" /> : <CameraOff className="w-3 h-3" />}
                {cameraEnabled ? 'Camera On' : 'Camera Off'}
              </button>
              {!isMobile && (
                <button
                  onClick={screenShareEnabled ? stopScreenShare : startScreenShare}
                  className={`inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-md border transition-colors ${
                    screenShareEnabled
                      ? 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100'
                      : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  {screenShareEnabled ? <Monitor className="w-3 h-3" /> : <MonitorOff className="w-3 h-3" />}
                  {screenShareEnabled ? 'Sharing' : 'Share Screen'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM PANEL — Recording / Transcript / Submit */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        {isTranscribing ? (
          <div className="flex items-center gap-2 text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Transcribing your answer...</span>
          </div>
        ) : showTranscriptReview ? (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Edit3 className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-semibold text-purple-700">Review Transcript</span>
            </div>
            <textarea
              value={transcript}
              onChange={handleEditTranscript}
              rows={3}
              className="w-full p-3 border border-purple-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-purple-300"
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
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
              <span className="text-red-600 font-medium">Recording...</span>
              <span className="text-gray-500 text-sm tabular-nums">
                {Math.floor(sessionDuration / 60)}:{String(sessionDuration % 60).padStart(2, '0')}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={handleStopRecording} className="inline-flex items-center gap-1.5 bg-gray-800 text-white text-sm px-4 py-2 rounded-lg hover:bg-gray-900 transition-colors">
                <StopCircle className="w-4 h-4" />
                Stop Recording
              </button>
            </div>
          </div>
        ) : inputMode === 'voice' ? (
          <div className="flex items-center gap-2">
            <button onClick={handleStartRecording} className="inline-flex items-center gap-1.5 bg-red-600 text-white text-sm px-5 py-2.5 rounded-lg hover:bg-red-700 transition-colors">
              <Mic className="w-4 h-4" />
              Start Recording
            </button>
            <button onClick={() => setInputMode('text')} className="inline-flex items-center gap-1.5 text-gray-500 text-sm px-4 py-2.5 rounded-lg hover:bg-gray-100 transition-colors">
              <Edit3 className="w-4 h-4" />
              Type Instead
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              placeholder="Type your answer here..."
              rows={2}
              className="flex-1 p-3 border border-gray-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e) }}
            />
            <div className="flex flex-col gap-1">
              <button type="submit" disabled={isSubmitting || !answer.trim() || !proctoringReady} className="bg-blue-600 text-white px-5 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex-1 flex items-center gap-1.5">
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Submit
              </button>
            </div>
          </form>
        )}
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-gray-400">
            {showTranscriptReview
              ? 'Edit the transcript if needed, then submit.'
              : isRecording
              ? 'Recording in progress. Click Stop when done.'
              : inputMode === 'voice'
              ? 'Speak your answer. You can review the transcript before submitting.'
              : 'Press Cmd/Ctrl + Enter to submit'}
          </p>
          {inputMode === 'text' && !isRecording && !showTranscriptReview && (
            <button
              onClick={() => setInputMode('voice')}
              className="text-xs text-blue-500 hover:text-blue-700"
            >
              Switch to Voice
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
