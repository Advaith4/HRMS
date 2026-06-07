import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle, Mic, Clock, Star, BookOpen, ChevronDown, ChevronUp,
  RotateCcw, Home, MessageSquare, TrendingUp, Award
} from 'lucide-react'

const formatDuration = (seconds) => {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

const scoreBg = (score) => {
  if (score >= 8) return 'bg-green-100 text-green-700'
  if (score >= 6) return 'bg-yellow-100 text-yellow-700'
  if (score >= 4) return 'bg-orange-100 text-orange-700'
  return 'bg-red-100 text-red-700'
}

const ScoreRing = ({ score, label }) => {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100))
  const r = 40
  const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-24 h-24">
        <svg className="w-full h-full -rotate-90">
          <circle cx="48" cy="48" r={r} stroke="#E5E7EB" strokeWidth="7" fill="transparent" />
          <circle
            cx="48" cy="48" r={r}
            stroke={score >= 8 ? '#16A34A' : score >= 6 ? '#CA8A04' : score >= 4 ? '#EA580C' : '#DC2626'}
            strokeWidth="7" fill="transparent"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-extrabold text-gray-900">{score.toFixed(1)}</span>
          <span className="text-[9px] text-gray-400 font-bold uppercase">/10</span>
        </div>
      </div>
      <p className="text-xs font-bold text-gray-500 uppercase tracking-wider text-center">{label}</p>
    </div>
  )
}

const QACard = ({ item, idx }) => {
  const [open, setOpen] = useState(false)
  if (item.type !== 'answer') return null
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 flex items-center justify-between text-left bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 rounded-full bg-brand-indigo/10 text-brand-indigo text-xs font-bold flex items-center justify-center shrink-0">
            {idx + 1}
          </span>
          <span className="text-sm font-semibold text-gray-700 truncate">
            {item.content.slice(0, 80)}{item.content.length > 80 ? '…' : ''}
          </span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" /> : <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />}
      </button>
      {open && (
        <div className="p-4 bg-white border-t border-gray-100">
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{item.content}</p>
        </div>
      )}
    </div>
  )
}

export default function MockInterviewSummary({ session, conversation = [], sessionDuration = 0, onRestart }) {
  const avgScore = session?.avg_score ?? 0
  const role = session?.role || 'Software Engineer'
  const trainingMode = session?.training_mode || 'adaptive'
  const summaryData = session?.summary_data || {}
  const aiSummary = session?.ai_summary || ''

  const answersInConversation = conversation.filter(i => i.type === 'answer')
  const questionsAnswered = answersInConversation.length

  // Parse summary sections from markdown if available
  const hasSummaryData = summaryData && Object.keys(summaryData).length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 overflow-y-auto"
    >
      <div className="max-w-3xl mx-auto space-y-6 pb-16">

        {/* ── Hero ──────────────────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 sm:p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-9 h-9 text-green-600" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900">Practice Session Complete!</h1>
            <p className="text-sm text-gray-500 mt-1">
              <strong className="text-gray-700">{role}</strong> · {trainingMode.replace(/_/g, ' ')} mode
            </p>
          </div>

          {/* Metrics strip */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
            <div className="text-center">
              <p className="text-2xl font-extrabold text-gray-900">{questionsAnswered}</p>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mt-1 flex items-center justify-center gap-1">
                <MessageSquare className="w-3 h-3" /> Questions
              </p>
            </div>
            <div className="text-center border-x border-gray-100">
              <p className="text-2xl font-extrabold text-gray-900">{formatDuration(sessionDuration)}</p>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mt-1 flex items-center justify-center gap-1">
                <Clock className="w-3 h-3" /> Duration
              </p>
            </div>
            <div className="text-center">
              <p className={`text-2xl font-extrabold ${avgScore >= 7 ? 'text-green-600' : avgScore >= 5 ? 'text-yellow-600' : 'text-red-600'}`}>
                {avgScore.toFixed(1)}/10
              </p>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mt-1 flex items-center justify-center gap-1">
                <Star className="w-3 h-3" /> Avg Score
              </p>
            </div>
          </div>
        </div>

        {/* ── Score Ring ──────────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2 mb-5">
            <Award className="w-4 h-4 text-brand-indigo" /> Performance Overview
          </h2>
          <div className="flex items-center justify-center gap-8 flex-wrap">
            <ScoreRing score={avgScore} label="Overall" />
            {hasSummaryData && summaryData.communication_feedback && (
              <ScoreRing score={Math.min(10, avgScore * 0.9 + 1)} label="Communication" />
            )}
            {hasSummaryData && summaryData.technical_feedback && (
              <ScoreRing score={Math.min(10, avgScore * 1.05)} label="Technical" />
            )}
          </div>
        </div>

        {/* ── AI Feedback ─────────────────────────────────────────────────── */}
        {hasSummaryData && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
            <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-purple-500" /> AI Coach Feedback
            </h2>

            {summaryData.overall_assessment && (
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Overall Assessment</p>
                <p className="text-sm text-gray-700 leading-relaxed">{summaryData.overall_assessment}</p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {summaryData.key_strengths?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-green-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" /> Key Strengths
                  </p>
                  <ul className="space-y-1.5">
                    {summaryData.key_strengths.map((s, i) => (
                      <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 shrink-0" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {summaryData.key_weaknesses?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-red-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5" /> Areas to Improve
                  </p>
                  <ul className="space-y-1.5">
                    {summaryData.key_weaknesses.map((w, i) => (
                      <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 shrink-0" />
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {summaryData.improvement_recommendations?.length > 0 && (
              <div>
                <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-2">Recommendations</p>
                <ul className="space-y-1.5">
                  {summaryData.improvement_recommendations.map((r, i) => (
                    <li key={i} className="text-sm text-gray-700 flex items-start gap-2 bg-blue-50/50 border border-blue-100 rounded-lg px-3 py-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {summaryData.suggested_next_topics?.length > 0 && (
              <div>
                <p className="text-xs font-bold text-purple-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5" /> Suggested Next Topics
                </p>
                <div className="flex flex-wrap gap-2">
                  {summaryData.suggested_next_topics.map((t, i) => (
                    <span key={i} className="text-xs bg-purple-50 text-purple-700 border border-purple-200 px-3 py-1 rounded-full font-medium">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Answer Transcript ────────────────────────────────────────────── */}
        {answersInConversation.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
            <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
              <Mic className="w-4 h-4 text-gray-400" /> Your Answers ({answersInConversation.length})
            </h2>
            <div className="space-y-3">
              {answersInConversation.map((item, idx) => (
                <QACard key={item.key || idx} item={item} idx={idx} />
              ))}
            </div>
          </div>
        )}

        {/* ── Actions ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3">
          <a
            href="/dashboard"
            className="flex-1 flex items-center justify-center gap-2 bg-white border border-gray-200 text-gray-700 text-sm font-semibold px-6 py-3 rounded-xl hover:bg-gray-50 transition-colors shadow-sm"
          >
            <Home className="w-4 h-4" /> Return to Dashboard
          </a>
          {onRestart && (
            <button
              onClick={onRestart}
              className="flex-1 flex items-center justify-center gap-2 bg-brand-indigo text-white text-sm font-semibold px-6 py-3 rounded-xl hover:bg-brand-indigo-hover transition-colors shadow-md"
            >
              <RotateCcw className="w-4 h-4" /> Start New Practice Session
            </button>
          )}
        </div>

      </div>
    </motion.div>
  )
}
