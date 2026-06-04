import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, AlertTriangle, XCircle, HelpCircle, RefreshCw, Shield } from 'lucide-react'
import { getCredibilityReport } from '../../api/interview'
import toast from 'react-hot-toast'

export default function CandidateCredibilityCard({ sessionId, onReport }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const fetchedRef = useRef(false)

  useEffect(() => {
    if (!sessionId || fetchedRef.current) return
    fetchedRef.current = true
    getCredibilityReport(sessionId, false).then(data => {
      setReport(data)
      if (onReport) onReport(data)
    }).catch(err => {
      console.error('Failed to load credibility report:', err)
      toast.error('Could not load credibility report')
    })
  }, [sessionId])

  const handleRefresh = async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const data = await getCredibilityReport(sessionId, true)
      setReport(data)
      if (onReport) onReport(data)
    } catch (err) {
      console.error('Failed to refresh credibility report:', err)
      toast.error('Could not refresh credibility report')
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = (score) => {
    if (score >= 75) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    if (score >= 40) return 'text-orange-600'
    return 'text-red-600'
  }

  const scoreBg = (score) => {
    if (score >= 75) return 'bg-green-100'
    if (score >= 60) return 'bg-yellow-100'
    if (score >= 40) return 'bg-orange-100'
    return 'bg-red-100'
  }

  const evidenceIcon = (evidence) => {
    if (evidence === 'strong') return <CheckCircle className="w-4 h-4 text-green-500" />
    if (evidence === 'moderate') return <CheckCircle className="w-4 h-4 text-blue-500" />
    if (evidence === 'weak') return <AlertTriangle className="w-4 h-4 text-yellow-500" />
    return <XCircle className="w-4 h-4 text-red-400" />
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-sm">Analyzing resume claims against interview evidence...</span>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Credibility Analysis</h3>
          <Shield className="w-4 h-4 text-gray-400" />
        </div>
        <p className="text-sm text-gray-400 mb-3">Compare resume claims against interview responses.</p>
        <button
          onClick={handleRefresh}
          className="inline-flex items-center gap-1.5 text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Run Credibility Check
        </button>
        <p className="text-[10px] text-gray-400 mt-2">Compares resume claims against interview responses.</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-5"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Credibility Analysis</h3>
        <button
          onClick={handleRefresh}
          className="text-xs text-gray-400 hover:text-gray-600 inline-flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" />
          Re-analyze
        </button>
      </div>

      <div className="flex items-center gap-6">
        <div className={`w-24 h-24 rounded-full ${scoreBg(report.credibility_score)} flex items-center justify-center`}>
          <span className={`text-3xl font-bold ${scoreColor(report.credibility_score)}`}>
            {report.credibility_score}
          </span>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">{report.recommendation}</p>
          <p className="text-sm text-gray-500">
            Resume: {report.resume_score} | Interview: {report.interview_avg_score !== null ? `${report.interview_avg_score.toFixed(1)}/10` : 'N/A'}
          </p>
          <span className="text-xs text-gray-400">Evidence-based skill verification</span>
        </div>
      </div>

      {report.supported_claims?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-green-600 mb-2 flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5" /> Supported Claims ({report.supported_claims.length})
          </h4>
          <div className="space-y-2">
            {report.supported_claims.map((item, i) => (
              <div key={i} className="flex items-start gap-2 text-sm p-2 bg-green-50 rounded-lg">
                {evidenceIcon(item.evidence)}
                <div>
                  <span className="font-medium text-gray-800">{item.claim}</span>
                  <p className="text-xs text-gray-500">{item.explanation}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.weak_claims?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-yellow-600 mb-2 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" /> Weak Claims ({report.weak_claims.length})
          </h4>
          <div className="space-y-2">
            {report.weak_claims.map((item, i) => (
              <div key={i} className="flex items-start gap-2 text-sm p-2 bg-yellow-50 rounded-lg">
                {evidenceIcon(item.evidence)}
                <div>
                  <span className="font-medium text-gray-800">{item.claim}</span>
                  <p className="text-xs text-gray-500">{item.explanation}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.missing_evidence?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-red-500 mb-2 flex items-center gap-1.5">
            <XCircle className="w-3.5 h-3.5" /> Missing Evidence ({report.missing_evidence.length})
          </h4>
          <div className="space-y-2">
            {report.missing_evidence.map((item, i) => (
              <div key={i} className="flex items-start gap-2 text-sm p-2 bg-red-50 rounded-lg">
                {evidenceIcon(item.evidence)}
                <div>
                  <span className="font-medium text-gray-800">{item.claim}</span>
                  <p className="text-xs text-gray-500">{item.explanation}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.followup_topics?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-blue-600 mb-2 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5" /> Suggested Follow-Up Topics
          </h4>
          <div className="flex flex-wrap gap-2">
            {report.followup_topics.map((topic, i) => (
              <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full border border-blue-100">
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-1.5 text-xs text-gray-400 pt-1 border-t border-gray-100">
        <Shield className="w-3 h-3" />
        Evidence-based skill verification. Not a lie detector.
      </div>
    </motion.div>
  )
}
