
import { motion } from 'framer-motion'
import { Award, FileText, MessageSquare, TrendingUp, Shield } from 'lucide-react'
import CandidateCredibilityCard from './CandidateCredibilityCard'

export default function InterviewSummary({ session, onRestart }) {
  if (!session) return null

  const avgScore = session.avg_score || 0
  const finalFeedback = session.final_feedback || ''
  const finalVerdict = session.final_verdict || ''

  const scoreColor = (score) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    if (score >= 4) return 'text-orange-600'
    return 'text-red-600'
  }

  const scoreBg = (score) => {
    if (score >= 8) return 'bg-green-100'
    if (score >= 6) return 'bg-yellow-100'
    if (score >= 4) return 'bg-orange-100'
    return 'bg-red-100'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Interview Complete</h1>
        <p className="text-gray-500">{session.role} — {session.training_mode} mode</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
          <FileText className="w-8 h-8 mx-auto mb-2 text-blue-500" />
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Resume Score</p>
          <p className="text-2xl font-bold text-blue-600">{session.resume_score ?? '—'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
          <MessageSquare className="w-8 h-8 mx-auto mb-2 text-purple-500" />
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Interview Score</p>
          <div className={`inline-flex items-center justify-center w-14 h-14 rounded-full ${scoreBg(avgScore)}`}>
            <span className={`text-xl font-bold ${scoreColor(avgScore)}`}>{avgScore.toFixed(1)}</span>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
          <TrendingUp className="w-8 h-8 mx-auto mb-2 text-green-500" />
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Credibility Score</p>
          <CandidateCredibilityCard sessionId={session.id} />
        </div>
      </div>

      {finalFeedback && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Award className="w-4 h-4" /> Final Feedback
          </h3>
          <p className="text-gray-700 whitespace-pre-wrap">{finalFeedback}</p>
          {finalVerdict && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm font-semibold text-blue-800">{finalVerdict}</p>
            </div>
          )}
        </div>
      )}

      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
        <p className="text-sm text-blue-700">
          Credibility analysis compares resume claims against interview evidence to help recruiters
          prioritize candidates. This is evidence-based skill verification — not a lie detector.
        </p>
      </div>

      {onRestart && (
        <div className="text-center pb-8">
          <button
            onClick={onRestart}
            className="bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Start New Interview
          </button>
        </div>
      )}
    </motion.div>
  )
}
