import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Award, FileText, MessageSquare, TrendingUp, Shield, Brain,
  Activity, AlertTriangle, CheckCircle, Info, Sparkles, Check,
  X, Clock, ChevronDown, ChevronUp, BarChart3, HelpCircle
} from 'lucide-react'
import {
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell
} from 'recharts'
import { getSession } from '../../api/interview'
import CandidateCredibilityCard from './CandidateCredibilityCard'
import { useAuthStore } from '../../store/authStore'
import toast from 'react-hot-toast'

const INTELLIGENCE_PENDING_STATUSES = new Set(['active', 'completed', 'analyzing'])

const isIntelligencePending = (status) => INTELLIGENCE_PENDING_STATUSES.has(status)

export default function InterviewSummary({ session: initialSession, onRestart }) {
  const viewerRole = useAuthStore(state => state.role)
  const isHrViewer = ['hr', 'admin', 'manager'].includes(viewerRole)
  const [session, setSession] = useState(initialSession)
  const [loadingIntelligence, setLoadingIntelligence] = useState(
    isIntelligencePending(initialSession?.status)
  )
  const [expandedTurn, setExpandedTurn] = useState(null)
  const pollAttemptRef = useRef(0)

  useEffect(() => {
    if (initialSession) {
      setSession(initialSession)
      setLoadingIntelligence(isIntelligencePending(initialSession.status))
    }
  }, [initialSession])

  // Poll while the backend background task is compiling the final report.
  useEffect(() => {
    if (!loadingIntelligence || !session?.id) return

    let cancelled = false
    let timeoutId
    const poll = async () => {
      try {
        const updated = await getSession(session.id)
        if (cancelled) return
        if (!isIntelligencePending(updated.status)) {
          setSession(updated)
          setLoadingIntelligence(false)
          if (updated.status === 'analyzed') {
            toast.success('Hiring intelligence analysis complete!')
          }
          return
        }
        pollAttemptRef.current += 1
      } catch (err) {
        console.error('Error polling session intelligence:', err)
        pollAttemptRef.current += 1
      }
      const delay = Math.min(12000, 3000 * Math.max(1, pollAttemptRef.current))
      timeoutId = window.setTimeout(poll, delay)
    }

    timeoutId = window.setTimeout(poll, 3000)
    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [loadingIntelligence, session?.id])

  if (!session) return null

  // Proctoring termination view
  if (session.status === 'cancelled') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-xl mx-auto bg-white rounded-xl border border-red-200 shadow-xl overflow-hidden mt-8 text-txt-primary"
      >
        <div className="p-6 text-center space-y-4">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto text-red-600 animate-pulse">
            <Shield className="w-8 h-8" />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-gray-900">Interview Cancelled</h1>
            <p className="text-sm text-gray-500">
              Your session for the <strong>{session.role}</strong> interview was terminated due to proctoring violations.
            </p>
          </div>

          <div className="bg-red-50 border border-red-100 text-red-700 rounded-lg p-4 text-sm text-left space-y-2">
            <p className="font-semibold flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-red-600"></span>
              Reason for Cancellation:
            </p>
            <p className="text-gray-600 italic">
              "{session.cancellation_reason || 'Proctoring violation limit exceeded (3).'}"
            </p>
          </div>

          <p className="text-xs text-gray-500 leading-relaxed">
            As part of the mandatory interview requirements, security violations are logged and reported to HR. 
            Please contact the hiring manager or administrator if you believe this was an error.
          </p>

          <div className="pt-4 border-t border-gray-100">
            <a
              href="/dashboard"
              className="inline-block bg-brand-indigo text-white text-xs font-semibold px-6 py-2.5 rounded-lg hover:bg-brand-indigo-hover transition-colors cursor-pointer"
            >
              Return to Careers Dashboard
            </a>
          </div>
        </div>
      </motion.div>
    )
  }

  // Synthesis loading state
  if (loadingIntelligence) {
    return (
      <div className="max-w-xl mx-auto bg-white border border-gray-200 rounded-xl shadow-xl p-8 mt-8 text-center space-y-6">
        <div className="relative w-20 h-20 mx-auto">
          <div className="absolute inset-0 rounded-full border-4 border-brand-indigo/20 border-t-brand-indigo animate-spin"></div>
          <div className="absolute inset-2.5 rounded-full border-4 border-purple-500/20 border-t-purple-500 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.2s' }}></div>
          <div className="absolute inset-5 rounded-full border-4 border-sky-400/20 border-t-sky-400 animate-spin animate-duration-700"></div>
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-gray-900 flex items-center justify-center gap-2">
            <Brain className="w-5 h-5 text-brand-indigo animate-pulse" />
            Interview completed. Generating final report.
          </h2>
          <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
            {isHrViewer
              ? 'Compiling competency profile, communication metrics, and hiring intelligence for review.'
              : 'Your responses have been submitted. The hiring team will review your interview shortly.'}
          </p>
        </div>
      </div>
    )
  }

  if (!isHrViewer) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-xl mx-auto bg-white rounded-xl border border-gray-200 shadow-xl p-8 mt-8 text-center space-y-6"
      >
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto text-green-600">
          <CheckCircle className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-gray-900">Interview Submitted</h1>
          <p className="text-sm text-gray-500 leading-relaxed">
            Thank you for completing your <strong>{session.role}</strong> interview.
            Your answers have been recorded and will be reviewed by the hiring team.
          </p>
        </div>
        <div className="pt-4 border-t border-gray-100 flex justify-center gap-3">
          <a
            href="/dashboard"
            className="bg-brand-indigo text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-brand-indigo-hover transition-colors"
          >
            Return to Careers Dashboard
          </a>
          {onRestart && (
            <button
              onClick={onRestart}
              className="bg-gray-100 text-gray-700 text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-gray-200 transition-colors border border-gray-300"
            >
              Start Practice Session
            </button>
          )}
        </div>
      </motion.div>
    )
  }

  const avgScore = session.avg_score || 0
  const finalFeedback = session.final_feedback || ''
  const finalVerdict = session.final_verdict || ''

  // Load JSON reports if present
  const competencyScores = typeof session.competency_scores === 'string' ? JSON.parse(session.competency_scores) : session.competency_scores
  const jobFitReport = typeof session.job_fit_report === 'string' ? JSON.parse(session.job_fit_report) : session.job_fit_report
  const communicationMetrics = typeof session.communication_metrics === 'string' ? JSON.parse(session.communication_metrics) : session.communication_metrics
  const behavioralReport = typeof session.behavioral_report === 'string' ? JSON.parse(session.behavioral_report) : session.behavioral_report
  const hiringRisks = typeof session.hiring_risks === 'string' ? JSON.parse(session.hiring_risks) : session.hiring_risks
  const timelineReplay = typeof session.timeline_replay === 'string' ? JSON.parse(session.timeline_replay) : session.timeline_replay
  const benchmarking = typeof session.benchmarking === 'string' ? JSON.parse(session.benchmarking) : session.benchmarking

  // Chart data formatting
  const competencyData = competencyScores ? [
    { subject: 'Tech Depth', A: competencyScores.technicalDepth || 0 },
    { subject: 'Problem Solving', A: competencyScores.problemSolving || 0 },
    { subject: 'Communication', A: competencyScores.communication || 0 },
    { subject: 'Leadership', A: competencyScores.leadership || 0 },
    { subject: 'System Design', A: competencyScores.systemDesign || 0 },
    { subject: 'Confidence', A: competencyScores.confidence || 0 },
    { subject: 'Domain Knowledge', A: competencyScores.domainKnowledge || 0 },
  ] : []

  const behavioralData = behavioralReport?.categories ? [
    { name: 'Technical', score: behavioralReport.categories.Technical || 0 },
    { name: 'Behavioral', score: behavioralReport.categories.Behavioral || 0 },
    { name: 'Situational', score: behavioralReport.categories.Situational || 0 },
    { name: 'Leadership', score: behavioralReport.categories.Leadership || 0 },
  ] : []

  const jobFitScore = jobFitReport?.jobFit || Math.round(avgScore * 10)
  const riskLevel = jobFitReport?.riskLevel || 'Low'

  const scoreColor = (score) => {
    if (score >= 8 || score >= 80) return 'text-green-600'
    if (score >= 6 || score >= 60) return 'text-yellow-600'
    if (score >= 4 || score >= 40) return 'text-orange-600'
    return 'text-red-600'
  }

  const scoreBg = (score) => {
    if (score >= 8 || score >= 80) return 'bg-green-100'
    if (score >= 6 || score >= 60) return 'bg-yellow-100'
    if (score >= 4 || score >= 40) return 'bg-orange-100'
    return 'bg-red-100'
  }

  const riskBadgeColor = (risk) => {
    if (risk === 'Low') return 'bg-green-50 text-green-700 border-green-200'
    if (risk === 'Medium') return 'bg-amber-50 text-amber-700 border-amber-200'
    return 'bg-red-50 text-red-700 border-red-200'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-6 text-txt-primary"
    >
      {/* Title block */}
      <div className="text-center space-y-1">
        <h1 className="text-3xl font-extrabold text-gray-900 flex items-center justify-center gap-2">
          <Sparkles className="w-7 h-7 text-brand-indigo" />
          Hiring Intelligence Report
        </h1>
        <p className="text-gray-500 font-medium">Candidate: {session.role} — {session.training_mode} mode</p>
      </div>

      {/* Row 1: Traditional Summary + Benchmarking Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center flex flex-col justify-between">
          <div>
            <FileText className="w-8 h-8 mx-auto mb-2 text-blue-500" />
            <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Resume Score</p>
          </div>
          <p className="text-3xl font-black text-blue-600">{session.resume_score ?? '—'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center flex flex-col justify-between">
          <div>
            <MessageSquare className="w-8 h-8 mx-auto mb-2 text-purple-500" />
            <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Interview Score</p>
          </div>
          <div className="my-1">
            <div className={`inline-flex items-center justify-center w-14 h-14 rounded-full ${scoreBg(avgScore)}`}>
              <span className={`text-xl font-bold ${scoreColor(avgScore)}`}>{avgScore.toFixed(1)}</span>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center flex flex-col justify-between">
          <div>
            <TrendingUp className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
            <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Credibility Score</p>
          </div>
          <div className="flex justify-center">
            <CandidateCredibilityCard sessionId={session.id} />
          </div>
        </div>
        
        {/* Benchmarking Widget */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col justify-between">
          <div className="text-center md:text-left">
            <BarChart3 className="w-8 h-8 mx-auto md:mx-0 mb-2 text-pink-500" />
            <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Benchmarking</p>
          </div>
          <div className="mt-1">
            {benchmarking?.insufficient_data ? (
              <div className="text-xs text-gray-400 bg-gray-50 border border-gray-100 rounded-lg p-2.5 text-center flex items-center justify-center gap-1.5">
                <Info className="w-4 h-4 shrink-0 text-gray-400" />
                Under Evaluation (Insufficient data)
              </div>
            ) : benchmarking ? (
              <div className="text-center space-y-1">
                <p className="text-2xl font-black text-pink-600">Top {benchmarking.percentile}%</p>
                <p className="text-[10px] text-gray-500">
                  Ranked #{benchmarking.ranking} of {benchmarking.total_candidates} candidates
                </p>
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center">No benchmark information available</p>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: Competency Radar + Job Fit Gauge */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Radar Chart Column */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 md:col-span-2 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <Brain className="w-4 h-4 text-brand-indigo" /> Competency Profile
          </h3>
          {competencyData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={competencyData}>
                  <PolarGrid stroke="#E2E8F0" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 10, fontWeight: 500 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: '#94A3B8' }} />
                  <Radar name="Candidate" dataKey="A" stroke="#2563EB" fill="#3B82F6" fillOpacity={0.35} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', fontSize: '12px' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400 text-sm">Competency details loading...</div>
          )}
        </div>

        {/* Job Fit Dial Column */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-col justify-between">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <Award className="w-4 h-4 text-brand-indigo" /> Job Alignment
          </h3>
          <div className="relative w-36 h-36 flex items-center justify-center mx-auto my-3">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="72" cy="72" r="60" className="stroke-gray-100" strokeWidth="8" fill="transparent" />
              <circle
                cx="72"
                cy="72"
                r="60"
                className="stroke-brand-indigo transition-all duration-1000 ease-out"
                strokeWidth="10"
                fill="transparent"
                strokeDasharray={2 * Math.PI * 60}
                strokeDashoffset={2 * Math.PI * 60 - (jobFitScore / 100) * (2 * Math.PI * 60)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-3xl font-extrabold text-gray-900">{jobFitScore}%</span>
              <span className="text-[10px] text-gray-500 uppercase font-semibold tracking-wider">Fit Index</span>
            </div>
          </div>
          <div className="space-y-1 text-center">
            <p className="text-xs text-gray-500">
              Recommended Role: <strong className="text-gray-800">{jobFitReport?.recommendedRole || session.role}</strong>
            </p>
            <div className="flex justify-center mt-1.5">
              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${riskBadgeColor(riskLevel)}`}>
                {riskLevel} Risk Profile
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Communication Metrics (Filler Words) + Behavioral Categories */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Communication Quality & Filler Words */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-purple-500" /> Communication Metrics
          </h3>
          
          {communicationMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Clarity', val: communicationMetrics.clarity },
                  { label: 'Vocabulary', val: communicationMetrics.vocabulary },
                  { label: 'Confidence', val: communicationMetrics.confidence },
                  { label: 'Conciseness', val: communicationMetrics.conciseness },
                ].map((item, idx) => (
                  <div key={idx} className="bg-gray-50 rounded-lg p-2.5 border border-gray-100 flex justify-between items-center">
                    <span className="text-xs font-semibold text-gray-600">{item.label}</span>
                    <span className="text-sm font-bold text-gray-900">{item.val ? item.val.toFixed(1) : '—'}/10</span>
                  </div>
                ))}
              </div>

              {/* Filler words badge block */}
              {communicationMetrics.fillerWords && (
                <div className="border-t border-gray-100 pt-3">
                  <p className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-2">Filler Words Counted</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(communicationMetrics.fillerWords).map(([word, count]) => {
                      const isHigh = count >= 4
                      return (
                        <span key={word} className={`px-2.5 py-1 rounded-full text-xs font-medium border flex items-center gap-1.5 ${
                          isHigh ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-gray-50 text-gray-600 border-gray-200'
                        }`}>
                          <span className="italic">"{word}"</span>
                          <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                            isHigh ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-700'
                          }`}>{count}</span>
                        </span>
                      )
                    })}
                  </div>
                  {Object.values(communicationMetrics.fillerWords).reduce((a, b) => a + b, 0) >= 10 && (
                    <p className="text-[10px] text-amber-600 flex items-start gap-1 mt-2.5 bg-amber-50 p-2 rounded-lg border border-amber-100">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      Linguistic pattern: Frequency of placeholder words suggests moderate candidate hesitation.
                    </p>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-gray-400 italic">Communication metrics loading...</p>
          )}
        </div>

        {/* Behavioral Breakdown Chart */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-500" /> Behavioral Categories
          </h3>
          {behavioralData.length > 0 ? (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={behavioralData} layout="vertical" margin={{ left: 10, right: 10, top: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis type="number" domain={[0, 10]} tick={{ fill: '#94A3B8', fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#475569', fontSize: 10, fontWeight: 500 }} width={75} />
                  <Tooltip contentStyle={{ fontSize: '11px', borderRadius: '6px' }} />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                    {behavioralData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B'][index % 4]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-xs text-gray-400 italic">Behavioral reports loading...</p>
          )}
        </div>
      </div>

      {/* Row 4: Strengths & Weaknesses lists */}
      {jobFitReport && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
            <h4 className="text-xs font-bold text-green-600 uppercase tracking-wider flex items-center gap-1.5 border-b border-gray-100 pb-2">
              <CheckCircle className="w-4 h-4 text-green-500" /> Key Strengths
            </h4>
            <ul className="space-y-2">
              {jobFitReport.strengths?.map((str, idx) => (
                <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                  <Check className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                  {str}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
            <h4 className="text-xs font-bold text-red-600 uppercase tracking-wider flex items-center gap-1.5 border-b border-gray-100 pb-2">
              <AlertTriangle className="w-4 h-4 text-red-500" /> Improvement Areas
            </h4>
            <ul className="space-y-2">
              {jobFitReport.weaknesses?.map((weak, idx) => (
                <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                  <X className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  {weak}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Row 5: Hiring Risks Flaggers */}
      {hiringRisks && hiringRisks.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <Shield className="w-4 h-4 text-red-500" /> Flagged Hiring Risks
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {hiringRisks.map((riskItem, idx) => (
              <div key={idx} className="bg-red-50/50 border border-red-100 rounded-lg p-4 space-y-2">
                <p className="text-sm font-semibold text-red-700 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                  {riskItem.risk}
                </p>
                <div className="text-xs text-gray-600 italic pl-6 border-l-2 border-red-200">
                  "{riskItem.evidence || 'Candidate did not offer specific depth on verification follow-up.'}"
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Row 6: Expandable Turn-by-Turn Timeline Replay */}
      {timelineReplay && timelineReplay.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-indigo" /> Turn-by-Turn Timeline Replay
          </h3>
          
          <div className="relative border-l border-gray-200 ml-4 pl-6 space-y-4">
            {timelineReplay.map((turn, idx) => {
              const isExpanded = expandedTurn === idx
              const turnScore = turn.score || 5
              const turnColorClass = turnScore >= 8 ? 'bg-green-500' : turnScore >= 6 ? 'bg-yellow-500' : 'bg-red-500'

              return (
                <div key={idx} className="relative">
                  {/* Timeline bubble */}
                  <span className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-2 border-white ring-4 ring-gray-50 flex items-center justify-center ${turnColorClass}`} />
                  
                  <div className="bg-gray-50 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors shadow-sm overflow-hidden">
                    <button
                      onClick={() => setExpandedTurn(isExpanded ? null : idx)}
                      className="w-full p-4 flex items-center justify-between text-left focus:outline-none"
                    >
                      <div className="space-y-1 pr-4 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold text-gray-400 uppercase">Turn {turn.turn}</span>
                          <span className="text-xs font-bold text-brand-indigo bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                            {turn.phase}
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-gray-800 truncate">
                          Q: {turn.question}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${scoreBg(turnScore)} ${scoreColor(turnScore)}`}>
                          Score: {turnScore}/10
                        </span>
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                      </div>
                    </button>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          <div className="p-4 border-t border-gray-200 bg-white space-y-3 text-xs leading-relaxed">
                            <div>
                              <p className="font-bold text-gray-500 uppercase tracking-wider mb-1">Full Question</p>
                              <p className="text-gray-800 text-sm font-medium">{turn.question}</p>
                            </div>
                            <div>
                              <p className="font-bold text-gray-500 uppercase tracking-wider mb-1">Candidate Answer Summary</p>
                              <p className="text-gray-700 bg-gray-50 p-2.5 rounded border border-gray-100 italic">"{turn.answer}"</p>
                            </div>

                            {/* Impact matrices */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                              {turn.competencyImpact && Object.keys(turn.competencyImpact).length > 0 && (
                                <div className="bg-blue-50/50 border border-blue-100 rounded p-2.5">
                                  <p className="font-bold text-blue-800 uppercase tracking-wider mb-1 flex items-center gap-1">
                                    <Brain className="w-3.5 h-3.5 text-blue-600" /> Competency Impact
                                  </p>
                                  <div className="space-y-1">
                                    {Object.entries(turn.competencyImpact).map(([comp, val]) => {
                                      const numericVal = parseFloat(val)
                                      const isPos = numericVal >= 0
                                      return (
                                        <div key={comp} className="flex justify-between text-[11px]">
                                          <span className="text-gray-600 capitalize">{comp.replace(/([A-Z])/g, ' $1')}</span>
                                          <span className={`font-bold ${isPos ? 'text-green-600' : 'text-red-600'}`}>
                                            {isPos ? '+' : ''}{numericVal.toFixed(1)}
                                          </span>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              )}
                              {turn.credibilityImpact && (turn.credibilityImpact.claim || turn.credibilityImpact.status) && (
                                <div className="bg-purple-50/50 border border-purple-100 rounded p-2.5">
                                  <p className="font-bold text-purple-800 uppercase tracking-wider mb-1 flex items-center gap-1">
                                    <Shield className="w-3.5 h-3.5 text-purple-600" /> Claim Verification
                                  </p>
                                  <div className="text-[11px] space-y-1">
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Claim Focus:</span>
                                      <strong className="text-gray-800">{turn.credibilityImpact.claim || 'General context'}</strong>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Verification:</span>
                                      <span className={`font-semibold capitalize ${
                                        turn.credibilityImpact.status === 'supported' ? 'text-green-600' :
                                        turn.credibilityImpact.status === 'weak' ? 'text-amber-600' : 'text-red-600'
                                      }`}>{turn.credibilityImpact.status || 'N/A'}</span>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Restart/Finish actions */}
      {onRestart && (
        <div className="text-center pb-8 pt-4 border-t border-gray-100 flex justify-center gap-3">
          <a
            href="/dashboard"
            className="bg-gray-100 text-gray-700 px-6 py-2.5 rounded-lg hover:bg-gray-200 transition-colors font-semibold text-sm border border-gray-300"
          >
            Careers Dashboard
          </a>
          <button
            onClick={onRestart}
            className="bg-brand-indigo text-white px-6 py-2.5 rounded-lg hover:bg-brand-indigo-hover transition-colors font-semibold text-sm shadow-md"
          >
            Start New Practice Session
          </button>
        </div>
      )}
    </motion.div>
  )
}
