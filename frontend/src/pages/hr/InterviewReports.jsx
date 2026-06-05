import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Cell, Legend, RadialBarChart, RadialBar,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from 'recharts'
import {
  Award, TrendingUp, AlertTriangle, CheckCircle, XCircle, Brain,
  ChevronDown, ChevronUp, UserCheck, ArrowUpRight, ThumbsUp,
  Users, Target, Shield, Zap, Search, X, Clock, BarChart3,
  Star, Activity, FileText, ExternalLink, RefreshCw,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import {
  getIntelligenceLeaderboard, getCandidateIntelligenceReport,
  compareCandidates, getTopCandidates, getFollowupQuestions,
  advanceCandidate, rejectCandidate,
} from '../../api/interview'

const RECOMMENDATION_COLORS = {
  'Strongly Recommended': { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30', bar: '#10B981' },
  'Recommended': { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', bar: '#3B82F6' },
  'Needs Review': { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30', bar: '#F59E0B' },
  'Not Recommended': { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', bar: '#EF4444' },
}

const scoreColor = (s) => {
  if (s >= 80) return '#10B981'
  if (s >= 60) return '#3B82F6'
  if (s >= 40) return '#F59E0B'
  return '#EF4444'
}

const TABS = [
  { id: 'leaderboard', label: 'Leaderboard', icon: Award },
  { id: 'top', label: 'Top Candidates', icon: Star },
  { id: 'compare', label: 'Compare', icon: Users },
]

export const InterviewReports = () => {
  const { role } = useAuthStore()
  const isHr = role === 'hr' || role === 'admin'
  const [activeTab, setActiveTab] = useState('leaderboard')
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const [candidateReport, setCandidateReport] = useState(null)
  const [detailTab, setDetailTab] = useState('matrix') // matrix | linguistic | timeline | proctoring
  const [expandedTurn, setExpandedTurn] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [compareIds, setCompareIds] = useState([])
  const [comparisonData, setComparisonData] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [topCandidates, setTopCandidates] = useState(null)
  const [topLoading, setTopLoading] = useState(false)
  const [followupQuestions, setFollowupQuestions] = useState([])
  const [followupLoading, setFollowupLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(null)
  const [sortField, setSortField] = useState('hiring_score')
  const [sortDir, setSortDir] = useState('desc')

  const loadLeaderboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getIntelligenceLeaderboard()
      setLeaderboard(data.leaderboard || [])
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadLeaderboard() }, [loadLeaderboard])

  const loadTopCandidates = useCallback(async () => {
    setTopLoading(true)
    try {
      const data = await getTopCandidates()
      setTopCandidates(data)
    } catch (e) {
      console.error(e)
    } finally {
      setTopLoading(false)
    }
  }, [])

  useEffect(() => { loadTopCandidates() }, [loadTopCandidates])

  const handleSelectCandidate = useCallback(async (candidateId) => {
    setSelectedCandidate(candidateId)
    setReportLoading(true)
    setFollowupQuestions([])
    setDetailTab('matrix')
    setExpandedTurn(null)
    try {
      const report = await getCandidateIntelligenceReport(candidateId)
      setCandidateReport(report)
    } catch (e) {
      console.error(e)
    } finally {
      setReportLoading(false)
    }
  }, [])

  const handleLoadFollowup = useCallback(async (sessionId) => {
    setFollowupLoading(true)
    try {
      const data = await getFollowupQuestions(sessionId)
      setFollowupQuestions(data.followup_questions || [])
    } catch (e) {
      console.error(e)
    } finally {
      setFollowupLoading(false)
    }
  }, [])

  const handleAdvance = useCallback(async (sessionId) => {
    setActionLoading(sessionId)
    try {
      await advanceCandidate(sessionId)
      loadLeaderboard()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(null)
    }
  }, [loadLeaderboard])

  const handleReject = useCallback(async (sessionId) => {
    setActionLoading(sessionId)
    try {
      await rejectCandidate(sessionId)
      loadLeaderboard()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(null)
    }
  }, [loadLeaderboard])

  const handleCompare = useCallback(async () => {
    if (compareIds.length < 2) return
    setCompareLoading(true)
    try {
      const data = await compareCandidates(compareIds)
      setComparisonData(data.comparison || [])
    } catch (e) {
      console.error(e)
    } finally {
      setCompareLoading(false)
    }
  }, [compareIds])

  const toggleCompareId = (id) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    )
  }

  const sortedLeaderboard = [...leaderboard].sort((a, b) => {
    const aVal = a[sortField] ?? 0
    const bVal = b[sortField] ?? 0
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal
  })

  const ScoreCircle = ({ score, label, size = 'md' }) => {
    const sizeClasses = size === 'lg' ? 'w-24 h-24 text-2xl' : size === 'sm' ? 'w-10 h-10 text-sm' : 'w-16 h-16 text-lg'
    return (
      <div className="flex flex-col items-center gap-1">
        <div className={`${sizeClasses} rounded-full flex items-center justify-center font-bold`}
          style={{ backgroundColor: `${scoreColor(score)}20`, color: scoreColor(score), border: `2px solid ${scoreColor(score)}` }}>
          {score}
        </div>
        {label && <span className="text-[10px] text-txt-tertiary uppercase tracking-wider">{label}</span>}
      </div>
    )
  }

  const Pill = ({ label, color = 'blue' }) => {
    const colors = {
      green: 'bg-green-500/10 text-green-400 border-green-500/20',
      yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      red: 'bg-red-500/10 text-red-400 border-red-500/20',
      blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    }
    return (
      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${colors[color] || colors.blue} mr-1.5 mb-1`}>
        {label}
      </span>
    )
  }

  const RecommendationBadge = ({ rec }) => {
    const colors = RECOMMENDATION_COLORS[rec] || RECOMMENDATION_COLORS['Needs Review']
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}>
        {rec === 'Strongly Recommended' && <ThumbsUp size={12} />}
        {rec === 'Recommended' && <CheckCircle size={12} />}
        {rec === 'Needs Review' && <AlertTriangle size={12} />}
        {rec === 'Not Recommended' && <XCircle size={12} />}
        {rec}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-txt-primary">Interview Intelligence Dashboard</h2>
          <p className="text-sm text-txt-tertiary mt-0.5">AI-powered hiring insights — combine resume, interview, and credibility scores</p>
        </div>
        {!isHr && (
          <span className="text-[11px] text-amber-400 bg-amber-500/10 px-3 py-1.5 rounded-full border border-amber-500/20">
            View-only mode
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-elevated p-1 rounded-xl border border-border-hover-custom w-fit">
        {TABS.map(tab => {
          const Icon = tab.icon
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id ? 'bg-brand-indigo text-white shadow-md' : 'text-txt-secondary hover:text-txt-primary'
              }`}>
              <Icon size={16} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* ── LEADERBOARD TAB ── */}
      {activeTab === 'leaderboard' && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Main table */}
          <div className="xl:col-span-2 bg-bg-elevated rounded-xl border border-border-hover-custom overflow-hidden">
            <div className="p-4 border-b border-border-hover-custom flex justify-between items-center">
              <h3 className="font-semibold text-txt-primary flex items-center gap-2">
                <Award size={18} className="text-brand-indigo" />
                Ranked Candidates ({leaderboard.length})
              </h3>
              <button onClick={loadLeaderboard} className="text-txt-tertiary hover:text-txt-primary transition-colors">
                <RefreshCw size={16} />
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-bg-page/60">
                  <tr className="text-left text-txt-tertiary text-[11px] uppercase tracking-wider">
                    <th className="px-4 py-3 font-medium">#</th>
                    <th className="px-4 py-3 font-medium">Candidate</th>
                    <th className="px-4 py-3 font-medium cursor-pointer" onClick={() => { setSortField('resume_score'); setSortDir(sortDir === 'desc' ? 'asc' : 'desc') }}>
                      Resume {sortField === 'resume_score' && (sortDir === 'desc' ? '↓' : '↑')}
                    </th>
                    <th className="px-4 py-3 font-medium cursor-pointer" onClick={() => { setSortField('interview_score'); setSortDir(sortDir === 'desc' ? 'asc' : 'desc') }}>
                      Interview {sortField === 'interview_score' && (sortDir === 'desc' ? '↓' : '↑')}
                    </th>
                    <th className="px-4 py-3 font-medium cursor-pointer" onClick={() => { setSortField('credibility_score'); setSortDir(sortDir === 'desc' ? 'asc' : 'desc') }}>
                      Credibility {sortField === 'credibility_score' && (sortDir === 'desc' ? '↓' : '↑')}
                    </th>
                    <th className="px-4 py-3 font-medium cursor-pointer" onClick={() => { setSortField('hiring_score'); setSortDir(sortDir === 'desc' ? 'asc' : 'desc') }}>
                      Hiring Score {sortField === 'hiring_score' && (sortDir === 'desc' ? '↓' : '↑')}
                    </th>
                    <th className="px-4 py-3 font-medium">Recommendation</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={8} className="text-center py-12 text-txt-tertiary">Loading leaderboard...</td></tr>
                  ) : error ? (
                    <tr><td colSpan={8} className="text-center py-12 text-red-400">{error}</td></tr>
                  ) : sortedLeaderboard.length === 0 ? (
                    <tr><td colSpan={8} className="text-center py-12 text-txt-tertiary">No interview data yet. Complete some interviews first.</td></tr>
                  ) : sortedLeaderboard.map((c, i) => (
                    <motion.tr key={c.candidate_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className={`border-t border-border-hover-custom hover:bg-bg-page/40 cursor-pointer transition-colors ${selectedCandidate === c.candidate_id ? 'bg-brand-indigo/5' : ''}`}
                      onClick={() => handleSelectCandidate(c.candidate_id)}>
                      <td className="px-4 py-3 text-txt-tertiary">{(i + 1).toString().padStart(2, '0')}</td>
                      <td className="px-4 py-3 font-medium text-txt-primary">{c.candidate_name}</td>
                      <td className="px-4 py-3"><ScoreCircle score={c.resume_score} size="sm" /></td>
                      <td className="px-4 py-3">
                        {c.interview_status === 'cancelled' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                            <AlertTriangle size={11} className="text-red-400" />
                            Cancelled
                          </span>
                        ) : (
                          <ScoreCircle score={c.interview_score} size="sm" />
                        )}
                      </td>
                      <td className="px-4 py-3"><ScoreCircle score={c.credibility_score} size="sm" /></td>
                      <td className="px-4 py-3"><span className="text-lg font-bold" style={{ color: scoreColor(c.hiring_score) }}>{c.hiring_score}</span></td>
                      <td className="px-4 py-3"><RecommendationBadge rec={c.recommendation} /></td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          c.status === 'Hired' ? 'bg-green-500/10 text-green-400' :
                          c.status === 'Rejected' ? 'bg-red-500/10 text-red-400' :
                          c.status === 'Shortlisted' ? 'bg-blue-500/10 text-blue-400' :
                          c.status === 'Under Review' ? 'bg-amber-500/10 text-amber-400' :
                          'bg-slate-500/10 text-slate-400'
                        }`}>{c.status}</span>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Candidate detail panel */}
          <div className="bg-bg-elevated rounded-xl border border-border-hover-custom overflow-hidden">
            <div className="p-4 border-b border-border-hover-custom flex justify-between items-center">
              <h3 className="font-semibold text-txt-primary flex items-center gap-2">
                <FileText size={16} className="text-brand-indigo" />
                Candidate Report
              </h3>
              {selectedCandidate && (
                <button onClick={() => { setSelectedCandidate(null); setCandidateReport(null); setFollowupQuestions([]) }}
                  className="text-txt-tertiary hover:text-txt-primary">
                  <X size={16} />
                </button>
              )}
            </div>
            {!selectedCandidate ? (
              <div className="p-8 text-center text-txt-tertiary">
                <Users size={32} className="mx-auto mb-3 opacity-40" />
                <p className="text-sm">Select a candidate from the leaderboard</p>
              </div>
            ) : reportLoading ? (
              <div className="p-8 text-center text-txt-tertiary">
                <div className="w-6 h-6 rounded-full border-2 border-brand-indigo border-t-transparent animate-spin mx-auto mb-3" />
                <p className="text-sm">Loading report...</p>
              </div>
            ) : candidateReport && (
              <div className="p-4 space-y-5 max-h-[70vh] overflow-y-auto">
                {/* Basic info */}
                <div>
                  <h4 className="font-semibold text-txt-primary">{candidateReport.candidate?.username}</h4>
                  <p className="text-xs text-txt-tertiary">Target: {candidateReport.candidate?.target_role || 'N/A'}</p>
                  <p className="text-xs text-txt-tertiary">Status: {candidateReport.application?.status}</p>
                </div>

                {/* Resolve session intelligence fields */}
                {(() => {
                  const latestSession = candidateReport.interview?.sessions?.[0]
                  const competencyScores = latestSession?.competency_scores
                  const jobFitReport = latestSession?.job_fit_report
                  const communicationMetrics = latestSession?.communication_metrics
                  const behavioralReport = latestSession?.behavioral_report
                  const hiringRisks = latestSession?.hiring_risks
                  const timelineReplay = latestSession?.timeline_replay
                  const benchmarking = latestSession?.benchmarking
                  const hasIntelligence = latestSession && (competencyScores || jobFitReport)

                  return (
                    <div className="space-y-4">
                      {/* Tab Selection Bar if intelligence is present */}
                      {hasIntelligence && (
                        <div className="flex border-b border-border-hover-custom mb-3 bg-bg-page/40 p-0.5 rounded-lg border">
                          {[
                            { id: 'matrix', label: 'Matrix' },
                            { id: 'linguistic', label: 'Linguistic/Risks' },
                            { id: 'timeline', label: 'Timeline Replay' },
                            { id: 'proctoring', label: 'Security/Proctor' }
                          ].map(tab => (
                            <button
                              key={tab.id}
                              onClick={() => setDetailTab(tab.id)}
                              className={`flex-1 py-1.5 text-center text-[11px] font-semibold rounded-md transition-all ${
                                detailTab === tab.id
                                  ? 'bg-brand-indigo text-white shadow-sm font-bold'
                                  : 'text-txt-secondary hover:text-txt-primary'
                              }`}
                            >
                              {tab.label}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* --- TAB CONTENT 1: HIRING MATRIX --- */}
                      {(!hasIntelligence || detailTab === 'matrix') && (
                        <div className="space-y-5">
                          {/* Composite score / Job Fit Dial */}
                          {hasIntelligence ? (
                            <div className="bg-bg-page/50 rounded-lg p-4 border border-border-hover-custom flex flex-col items-center">
                              <h5 className="text-[11px] font-semibold text-txt-secondary uppercase tracking-wider mb-2 self-start">Hiring Score & Fit Index</h5>
                              <div className="flex items-center justify-around w-full gap-4">
                                <div className="relative w-28 h-28 flex items-center justify-center shrink-0">
                                  <svg className="w-full h-full transform -rotate-90">
                                    <circle cx="56" cy="56" r="46" className="stroke-bg-page" strokeWidth="6" fill="transparent" />
                                    <circle
                                      cx="56"
                                      cy="56"
                                      r="46"
                                      className="stroke-brand-indigo transition-all duration-1000 ease-out"
                                      strokeWidth="8"
                                      fill="transparent"
                                      strokeDasharray={2 * Math.PI * 46}
                                      strokeDashoffset={2 * Math.PI * 46 - ((jobFitReport?.jobFit || 0) / 100) * (2 * Math.PI * 46)}
                                      strokeLinecap="round"
                                    />
                                  </svg>
                                  <div className="absolute flex flex-col items-center">
                                    <span className="text-xl font-black text-txt-primary">{jobFitReport?.jobFit || 0}%</span>
                                    <span className="text-[8px] text-txt-tertiary uppercase font-bold tracking-wider">Job Fit</span>
                                  </div>
                                </div>
                                
                                <div className="space-y-1.5 flex-1">
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="text-txt-tertiary w-14 truncate">Resume</span>
                                    <div className="flex-1 h-1.5 bg-bg-page rounded-full overflow-hidden">
                                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${candidateReport.hiring?.resume_weight || 0}%` }} />
                                    </div>
                                    <span className="text-txt-primary font-medium w-8 text-right">{candidateReport.hiring?.resume_weight || 0}</span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="text-txt-tertiary w-14 truncate">Interview</span>
                                    <div className="flex-1 h-1.5 bg-bg-page rounded-full overflow-hidden">
                                      <div className="h-full bg-green-500 rounded-full" style={{ width: `${candidateReport.hiring?.interview_weight || 0}%` }} />
                                    </div>
                                    <span className="text-txt-primary font-medium w-8 text-right">{candidateReport.hiring?.interview_weight || 0}</span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="text-txt-tertiary w-14 truncate">Credibility</span>
                                    <div className="flex-1 h-1.5 bg-bg-page rounded-full overflow-hidden">
                                      <div className="h-full bg-purple-500 rounded-full" style={{ width: `${candidateReport.hiring?.credibility_weight || 0}%` }} />
                                    </div>
                                    <span className="text-txt-primary font-medium w-8 text-right">{candidateReport.hiring?.credibility_weight || 0}</span>
                                  </div>
                                </div>
                              </div>
                              <div className="mt-3 text-center w-full flex justify-between items-center text-xs">
                                <RecommendationBadge rec={candidateReport.hiring?.recommendation || 'Needs Review'} />
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                  jobFitReport?.riskLevel === 'Low' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                                  jobFitReport?.riskLevel === 'Medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                  'bg-red-500/10 text-red-400 border-red-500/20'
                                }`}>
                                  {jobFitReport?.riskLevel || 'Low'} Risk
                                </span>
                              </div>
                            </div>
                          ) : (
                            <div className="bg-bg-page/50 rounded-lg p-4 border border-border-hover-custom">
                              <h5 className="text-xs font-semibold text-txt-secondary uppercase tracking-wider mb-3">Hiring Score</h5>
                              <div className="flex items-center justify-center gap-6">
                                <ScoreCircle score={candidateReport.hiring?.hiring_score || 0} label="Overall" size="lg" />
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="text-txt-tertiary w-20">Resume (35%)</span>
                                    <div className="flex-1 h-1.5 bg-bg-page rounded-full overflow-hidden">
                                      <div className="h-full rounded-full" style={{ width: `${candidateReport.hiring?.resume_weight || 0}%`, backgroundColor: '#3B82F6' }} />
                                    </div>
                                    <span className="text-txt-primary font-medium w-8 text-right">{candidateReport.hiring?.resume_weight || 0}</span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="text-txt-tertiary w-20">Interview (40%)</span>
                                    <div className="flex-1 h-1.5 bg-bg-page rounded-full overflow-hidden">
                                      <div className="h-full rounded-full" style={{ width: `${candidateReport.hiring?.interview_weight || 0}%`, backgroundColor: '#10B981' }} />
                                    </div>
                                    <span className="text-txt-primary font-medium w-8 text-right">{candidateReport.hiring?.interview_weight || 0}</span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs">
                                    <span className="text-txt-tertiary w-20">Credibility (25%)</span>
                                    <div className="flex-1 h-1.5 bg-bg-page rounded-full overflow-hidden">
                                      <div className="h-full rounded-full" style={{ width: `${candidateReport.hiring?.grid_weight || candidateReport.hiring?.credibility_weight || 0}%`, backgroundColor: '#8B5CF6' }} />
                                    </div>
                                    <span className="text-txt-primary font-medium w-8 text-right">{candidateReport.hiring?.grid_weight || candidateReport.hiring?.credibility_weight || 0}</span>
                                  </div>
                                </div>
                              </div>
                              <div className="mt-3 text-center">
                                <RecommendationBadge rec={candidateReport.hiring?.recommendation || 'Needs Review'} />
                              </div>
                            </div>
                          )}

                          {/* Benchmarking Fallback widget */}
                          {hasIntelligence && (
                            <div className="bg-bg-page/50 rounded-lg p-3 border border-border-hover-custom flex items-center gap-3">
                              <BarChart3 size={16} className="text-pink-500" />
                              <div className="text-xs">
                                <p className="font-bold text-txt-secondary uppercase tracking-wider text-[10px]">Benchmarking percentile</p>
                                {benchmarking?.insufficient_data ? (
                                  <span className="text-txt-tertiary italic text-[11px]">Under Evaluation (insufficient candidate data)</span>
                                ) : (
                                  <span className="text-txt-primary font-semibold">
                                    Ranked #{benchmarking?.ranking} of {benchmarking?.total_candidates} candidates (Top {benchmarking?.percentile}% percentile)
                                  </span>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Competency Radar Widget */}
                          {hasIntelligence && competencyScores && (
                            <div className="bg-bg-page/50 rounded-lg p-3 border border-border-hover-custom space-y-2">
                              <h5 className="text-[11px] font-bold text-txt-secondary uppercase tracking-wider flex items-center gap-1.5">
                                <Brain size={13} className="text-brand-indigo" /> Competency Breakdown
                              </h5>
                              <div className="h-52">
                                <ResponsiveContainer width="100%" height="100%">
                                  <RadarChart cx="50%" cy="50%" outerRadius="65%" data={[
                                    { subject: 'Tech Depth', A: competencyScores.technicalDepth || 0 },
                                    { subject: 'Problem Solv', A: competencyScores.problemSolving || 0 },
                                    { subject: 'Comm', A: competencyScores.communication || 0 },
                                    { subject: 'Leadership', A: competencyScores.leadership || 0 },
                                    { subject: 'Sys Design', A: competencyScores.systemDesign || 0 },
                                    { subject: 'Confidence', A: competencyScores.confidence || 0 },
                                    { subject: 'Domain', A: competencyScores.domainKnowledge || 0 }
                                  ]}>
                                    <PolarGrid stroke="#CBD5E1" />
                                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 8, fontWeight: 500 }} />
                                    <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: '#94A3B8', fontSize: 8 }} />
                                    <Radar name="Candidate" dataKey="A" stroke="#2563EB" fill="#3B82F6" fillOpacity={0.3} />
                                    <Tooltip contentStyle={{ fontSize: '10px', borderRadius: '4px' }} />
                                  </RadarChart>
                                </ResponsiveContainer>
                              </div>
                            </div>
                          )}

                          {/* Behavioral breakdown categories */}
                          {hasIntelligence && behavioralReport?.categories && (
                            <div className="bg-bg-page/50 rounded-lg p-3 border border-border-hover-custom space-y-2">
                              <h5 className="text-[11px] font-bold text-txt-secondary uppercase tracking-wider">
                                Behavioral Categories
                              </h5>
                              <div className="grid grid-cols-2 gap-2">
                                {Object.entries(behavioralReport.categories).map(([cat, val]) => (
                                  <div key={cat} className="bg-bg-page p-2 rounded border border-border-hover-custom text-xs">
                                    <div className="flex justify-between font-medium text-txt-secondary mb-1">
                                      <span>{cat}</span>
                                      <span>{val ? val.toFixed(1) : '0'}/10</span>
                                    </div>
                                    <div className="h-1 bg-border-custom rounded-full overflow-hidden">
                                      <div className="h-full bg-brand-indigo rounded-full" style={{ width: `${(val || 0) * 10}%` }} />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Strength analysis */}
                          {candidateReport.analysis?.strengths?.length > 0 && (
                            <div>
                              <h5 className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                <TrendingUp size={14} /> Top Strengths
                              </h5>
                              <div className="flex flex-wrap gap-1">
                                {candidateReport.analysis.strengths.map((s, i) => (
                                  <Pill key={i} label={typeof s === 'string' ? s : s.name || s.skill || JSON.stringify(s)} color="green" />
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Concern analysis */}
                          {candidateReport.analysis?.weaknesses?.length > 0 && (
                            <div>
                              <h5 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                <AlertTriangle size={14} /> Potential Concerns
                              </h5>
                              <div className="flex flex-wrap gap-1">
                                {candidateReport.analysis.weaknesses.map((w, i) => (
                                  <Pill key={i} label={typeof w === 'string' ? w : w.name || w.skill || JSON.stringify(w)} color="red" />
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Credibility details (legacy layout for compatibility) */}
                          {!hasIntelligence && candidateReport.credibility && (
                            <div className="bg-bg-page/50 rounded-lg p-3 border border-border-hover-custom">
                              <h5 className="text-xs font-semibold text-txt-secondary uppercase tracking-wider mb-3 flex items-center gap-1.5">
                                <Shield size={14} /> Credibility Analysis
                              </h5>
                              <div className="flex items-center gap-3 mb-3">
                                <ScoreCircle score={candidateReport.credibility.credibility_score || 0} size="sm" />
                                <span className="text-xs text-txt-tertiary">Source: {candidateReport.credibility.source}</span>
                              </div>

                              {(candidateReport.credibility.supported_claims || []).length > 0 && (
                                <div className="mb-2">
                                  <p className="text-[10px] text-green-400 font-medium mb-1">Supported Claims ({candidateReport.credibility.supported_claims.length})</p>
                                  {candidateReport.credibility.supported_claims.slice(0, 3).map((c, i) => (
                                    <p key={i} className="text-[11px] text-txt-secondary flex items-start gap-1.5 mb-0.5">
                                      <CheckCircle size={10} className="text-green-400 mt-0.5 shrink-0" />
                                      {typeof c === 'string' ? c : c.claim || c.name || ''}
                                    </p>
                                  ))}
                                </div>
                              )}

                              {(candidateReport.credibility.weak_claims || []).length > 0 && (
                                <div className="mb-2">
                                  <p className="text-[10px] text-yellow-400 font-medium mb-1">Weak Claims ({candidateReport.credibility.weak_claims.length})</p>
                                  {candidateReport.credibility.weak_claims.slice(0, 2).map((c, i) => (
                                    <p key={i} className="text-[11px] text-txt-secondary flex items-start gap-1.5 mb-0.5">
                                      <AlertTriangle size={10} className="text-yellow-400 mt-0.5 shrink-0" />
                                      {typeof c === 'string' ? c : c.claim || c.name || ''}
                                    </p>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* --- TAB CONTENT 2: LINGUISTIC & RISKS --- */}
                      {hasIntelligence && detailTab === 'linguistic' && (
                        <div className="space-y-4">
                          {/* Communication quality panel */}
                          {communicationMetrics && (
                            <div className="bg-bg-page/50 rounded-lg p-3 border border-border-hover-custom space-y-3">
                              <h5 className="text-[11px] font-bold text-txt-secondary uppercase tracking-wider flex items-center gap-1.5">
                                <MessageSquare size={13} className="text-purple-500" /> Communication Quality
                              </h5>
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                {[
                                  { label: 'Clarity', val: communicationMetrics.clarity },
                                  { label: 'Vocabulary', val: communicationMetrics.vocabulary },
                                  { label: 'Confidence', val: communicationMetrics.confidence },
                                  { label: 'Conciseness', val: communicationMetrics.conciseness }
                                ].map((item, idx) => (
                                  <div key={idx} className="bg-bg-page p-2 rounded border border-border-hover-custom flex justify-between">
                                    <span className="text-txt-secondary">{item.label}</span>
                                    <span className="font-bold text-txt-primary">{item.val ? item.val.toFixed(1) : '—'}/10</span>
                                  </div>
                                ))}
                              </div>

                              {/* Filler words list */}
                              {communicationMetrics.fillerWords && (
                                <div className="border-t border-border-hover-custom pt-2">
                                  <p className="text-[10px] text-txt-tertiary font-bold uppercase tracking-wider mb-1.5">Filler Words</p>
                                  <div className="flex flex-wrap gap-1">
                                    {Object.entries(communicationMetrics.fillerWords).map(([word, count]) => (
                                      <span key={word} className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-bg-page border border-border-hover-custom text-txt-secondary">
                                        "{word}": <strong className="text-txt-primary">{count}</strong>
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Recruiter Hiring Risks Flag boxes */}
                          {hiringRisks && (
                            <div className="space-y-2">
                              <h5 className="text-[11px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
                                <Shield size={13} className="text-red-400" /> Recruiter Hiring Risks
                              </h5>
                              {hiringRisks.length > 0 ? (
                                <div className="space-y-2">
                                  {hiringRisks.map((riskItem, rIdx) => (
                                    <div key={rIdx} className="bg-red-500/5 border border-red-500/10 rounded-lg p-3 space-y-1.5">
                                      <p className="text-xs font-semibold text-red-400 flex items-start gap-1.5">
                                        <AlertTriangle size={12} className="text-red-400 mt-0.5 shrink-0" />
                                        {riskItem.risk}
                                      </p>
                                      <div className="text-[10px] text-txt-secondary pl-4 border-l-2 border-red-500/20 italic">
                                        "{riskItem.evidence || 'Verification challenge failed.'}"
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-xs text-txt-tertiary italic">No technical credibility or verification risks flagged.</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* --- TAB CONTENT 3: TIMELINE REPLAY --- */}
                      {hasIntelligence && detailTab === 'timeline' && timelineReplay && (
                        <div className="space-y-3">
                          <h5 className="text-[11px] font-bold text-txt-secondary uppercase tracking-wider flex items-center gap-1.5">
                            <Activity size={13} className="text-brand-indigo" /> Expandable Timeline Stepper
                          </h5>
                          
                          <div className="relative border-l border-border-hover-custom ml-3 pl-4 space-y-2">
                            {timelineReplay.map((turn, tIdx) => {
                              const isTurnExpanded = expandedTurn === tIdx
                              const scoreColorClass = turn.score >= 8 ? 'bg-green-500' : turn.score >= 6 ? 'bg-yellow-500' : 'bg-red-500'

                              return (
                                <div key={tIdx} className="relative">
                                  {/* Stepper bubble */}
                                  <span className={`absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full border border-white ${scoreColorClass}`} />
                                  
                                  <div className="bg-bg-page/40 border border-border-hover-custom rounded-lg overflow-hidden text-xs">
                                    <button
                                      onClick={() => setExpandedTurn(isTurnExpanded ? null : tIdx)}
                                      className="w-full p-2.5 flex items-center justify-between text-left focus:outline-none"
                                    >
                                      <div className="min-w-0 pr-2">
                                        <div className="flex items-center gap-1.5 mb-0.5">
                                          <span className="text-[9px] font-bold text-txt-tertiary">Turn {turn.turn}</span>
                                          <span className="text-[9px] font-semibold text-brand-indigo bg-brand-indigo/10 px-1.5 py-0.2 rounded">
                                            {turn.phase}
                                          </span>
                                        </div>
                                        <p className="font-semibold text-txt-primary truncate">
                                          Q: {turn.question}
                                        </p>
                                      </div>
                                      <div className="flex items-center gap-2 shrink-0">
                                        <span className="text-[10px] font-bold text-txt-secondary">{turn.score}/10</span>
                                        {isTurnExpanded ? <ChevronUp size={12} className="text-txt-tertiary" /> : <ChevronDown size={12} className="text-txt-tertiary" />}
                                      </div>
                                    </button>

                                    {isTurnExpanded && (
                                      <div className="p-2.5 border-t border-border-hover-custom bg-bg-surface space-y-2 text-[11px] leading-relaxed">
                                        <div>
                                          <p className="font-bold text-txt-tertiary uppercase text-[9px] mb-0.5">Question Summary</p>
                                          <p className="text-txt-primary font-medium">{turn.question}</p>
                                        </div>
                                        <div>
                                          <p className="font-bold text-txt-tertiary uppercase text-[9px] mb-0.5">Answer Summary</p>
                                          <p className="text-txt-secondary italic bg-bg-page p-2 rounded">"{turn.answer}"</p>
                                        </div>
                                        
                                        {/* Turn competency and credibility impacts */}
                                        <div className="grid grid-cols-2 gap-2 pt-1">
                                          {turn.competencyImpact && Object.keys(turn.competencyImpact).length > 0 && (
                                            <div className="bg-brand-indigo/5 p-2 rounded border border-brand-indigo/10">
                                              <p className="font-bold text-brand-indigo uppercase text-[9px] mb-1">Competency Impact</p>
                                              {Object.entries(turn.competencyImpact).map(([comp, val]) => (
                                                <div key={comp} className="flex justify-between text-[10px]">
                                                  <span className="text-txt-secondary capitalize">{comp.replace(/([A-Z])/g, ' $1')}</span>
                                                  <span className={`font-bold ${parseFloat(val) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                    {parseFloat(val) >= 0 ? '+' : ''}{parseFloat(val).toFixed(1)}
                                                  </span>
                                                </div>
                                              ))}
                                            </div>
                                          )}
                                          {turn.credibilityImpact && (turn.credibilityImpact.claim || turn.credibilityImpact.status) && (
                                            <div className="bg-purple-500/5 p-2 rounded border border-purple-500/10">
                                              <p className="font-bold text-purple-500 uppercase text-[9px] mb-1">Claim Verification</p>
                                              <div className="text-[10px] space-y-0.5">
                                                <div className="flex justify-between">
                                                  <span className="text-txt-secondary">Claim:</span>
                                                  <span className="font-bold text-txt-primary truncate max-w-[50px]">{turn.credibilityImpact.claim || 'General'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                  <span className="text-txt-secondary">Status:</span>
                                                  <span className={`font-bold ${
                                                    turn.credibilityImpact.status === 'supported' ? 'text-green-500' :
                                                    turn.credibilityImpact.status === 'weak' ? 'text-amber-500' : 'text-red-500'
                                                  }`}>{turn.credibilityImpact.status || 'N/A'}</span>
                                                </div>
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      {/* --- TAB CONTENT 4: PROCTORING SECURITY --- */}
                      {(!hasIntelligence || detailTab === 'proctoring') && (
                        <div className="space-y-4">
                          {/* Proctoring Violations Log */}
                          {(() => {
                            const proctoredSessions = candidateReport.interview?.sessions?.filter(s => s.violations_count > 0 || s.status === 'cancelled') || []
                            if (proctoredSessions.length === 0) {
                              return <p className="text-xs text-txt-tertiary italic p-3 text-center bg-bg-page/40 rounded-lg border border-border-hover-custom">No proctoring violations recorded for this candidate.</p>
                            }
                            return (
                              <div className="space-y-3">
                                <h5 className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
                                  <Shield size={14} /> Proctoring Violations Log
                                </h5>
                                
                                {proctoredSessions.map((sessionItem, idx) => (
                                  <div key={sessionItem.id || idx} className="space-y-2 bg-red-500/5 p-3 rounded-lg border border-red-500/10">
                                    <div className="flex items-center justify-between text-xs border-b border-red-500/10 pb-1.5">
                                      <span className="text-txt-secondary font-medium">Session: {sessionItem.training_mode} mode</span>
                                      <span className={`px-2 py-0.5 rounded font-bold uppercase tracking-wider text-[10px] ${
                                        sessionItem.status === 'cancelled' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                      }`}>
                                        {sessionItem.status === 'cancelled' ? 'Cancelled' : `${sessionItem.violations_count} Violations`}
                                      </span>
                                    </div>
                                    
                                    {sessionItem.cancellation_reason && (
                                      <div className="text-xs text-red-400 bg-red-950/20 border border-red-500/10 p-2 rounded italic">
                                        <strong>Reason:</strong> "{sessionItem.cancellation_reason}"
                                      </div>
                                    )}
                                    
                                    {sessionItem.violations && sessionItem.violations.length > 0 ? (
                                      <div className="space-y-1 pt-1">
                                        {sessionItem.violations.map((v, vidx) => (
                                          <div key={vidx} className="bg-bg-page/60 p-2 rounded border border-border-hover-custom flex items-start gap-2 text-[10px]">
                                            <AlertTriangle size={12} className="text-amber-500 mt-0.5 shrink-0" />
                                            <div className="flex-1 min-w-0">
                                              <div className="flex justify-between text-txt-tertiary text-[9px] mb-0.5">
                                                <span className="font-semibold text-txt-secondary uppercase tracking-wider text-[8px]">{v.type || v.violation_type || 'Violation'}</span>
                                                <span>{v.timestamp ? new Date(v.timestamp).toLocaleTimeString() : ''}</span>
                                              </div>
                                              <p className="text-txt-primary">{v.detail}</p>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    ) : (
                                      <p className="text-xs text-txt-tertiary italic">No detailed logs found.</p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )
                          })()}
                        </div>
                      )}

                      {/* Timeline (legacy view only for compatibility) */}
                      {!hasIntelligence && candidateReport.interview?.timeline?.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-txt-secondary uppercase tracking-wider mb-3 flex items-center gap-1.5">
                            <Activity size={14} /> Interview Timeline
                          </h5>
                          <div className="space-y-2 max-h-40 overflow-y-auto">
                            {candidateReport.interview.timeline.map((t, i) => (
                              <div key={i} className="flex items-start gap-2 text-xs">
                                <div className="w-1 h-full min-h-[24px] rounded-full mt-1.5 shrink-0"
                                  style={{ backgroundColor: scoreColor(t.score * 10 || 0) }} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex justify-between items-center">
                                    <span className="text-txt-primary font-medium truncate">{t.question?.substring(0, 60)}...</span>
                                    <span className="text-txt-tertiary shrink-0 ml-2">Q{i + 1}</span>
                                  </div>
                                  <div className="flex gap-3 text-[10px] text-txt-tertiary">
                                    <span>Score: {t.score}/10</span>
                                    <span>Difficulty: {t.difficulty}</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })()}

                {/* Action buttons */}
                {isHr && candidateReport.interview?.sessions?.[0] && (
                  <div className="flex gap-2 pt-2 border-t border-border-hover-custom">
                    <button onClick={() => handleAdvance(candidateReport.interview.sessions[0].id)}
                      disabled={actionLoading === candidateReport.interview.sessions[0].id}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-green-500/10 text-green-400 border border-green-500/30 rounded-lg text-xs font-medium hover:bg-green-500/20 transition-colors disabled:opacity-50">
                      <UserCheck size={14} /> {actionLoading === candidateReport.interview.sessions[0].id ? '...' : 'Advance'}
                    </button>
                    <button onClick={() => handleReject(candidateReport.interview.sessions[0].id)}
                      disabled={actionLoading === candidateReport.interview.sessions[0].id}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg text-xs font-medium hover:bg-red-500/20 transition-colors disabled:opacity-50">
                      <XCircle size={14} /> {actionLoading === candidateReport.interview.sessions[0].id ? '...' : 'Reject'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TOP CANDIDATES TAB ── */}
      {activeTab === 'top' && (
        <div className="space-y-6">
          {topLoading ? (
            <div className="text-center py-12 text-txt-tertiary">Loading top candidates...</div>
          ) : !topCandidates ? (
            <div className="text-center py-12 text-txt-tertiary">No data available</div>
          ) : (
            <>
              {/* Metric summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'Top 5 Candidates', value: topCandidates.top_5?.length || 0, icon: Star, color: '#10B981' },
                  { label: 'Highest Credibility', value: topCandidates.highest_credibility?.[0]?.candidate_name || 'N/A', icon: Shield, color: '#8B5CF6', isName: true },
                  { label: 'Highest Interview', value: topCandidates.highest_interview_score?.[0]?.candidate_name || 'N/A', icon: TrendingUp, color: '#3B82F6', isName: true },
                  { label: 'Highest Overall', value: topCandidates.highest_overall?.[0]?.candidate_name || 'N/A', icon: Award, color: '#F59E0B', isName: true },
                ].map((card, i) => {
                  const Icon = card.icon
                  return (
                    <div key={i} className="bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon size={16} style={{ color: card.color }} />
                        <span className="text-xs text-txt-tertiary">{card.label}</span>
                      </div>
                      <p className={`text-lg font-bold ${card.isName ? 'text-txt-primary truncate' : ''}`} style={{ color: card.isName ? undefined : card.color }}>
                        {card.value}
                      </p>
                    </div>
                  )
                })}
              </div>

              {/* Top 5 chart */}
              {topCandidates.top_5?.length > 0 && (
                <div className="bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
                  <h3 className="font-semibold text-txt-primary mb-4 flex items-center gap-2">
                    <Star size={16} className="text-amber-400" />
                    Top 5 Candidates — Composite Score Breakdown
                  </h3>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={topCandidates.top_5.map(c => ({ ...c, name: c.candidate_name }))} layout="vertical" margin={{ left: 80, right: 20, top: 10, bottom: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2A3F5F" />
                        <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94A3B8', fontSize: 11 }} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#F1F5F9', fontSize: 11 }} width={80} />
                        <Tooltip contentStyle={{ background: '#1A2236', border: '1px solid #2A3F5F', borderRadius: 8, fontSize: 12 }} />
                        <Legend wrapperStyle={{ fontSize: 11, color: '#94A3B8' }} />
                        <Bar dataKey="resume_score" name="Resume Score" stackId="a" fill="#3B82F6" />
                        <Bar dataKey="interview_score" name="Interview Score" stackId="a" fill="#10B981" />
                        <Bar dataKey="credibility_score" name="Credibility Score" stackId="a" fill="#8B5CF6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Highest credibility panel */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
                  <h4 className="text-sm font-semibold text-txt-primary mb-3 flex items-center gap-2">
                    <Shield size={14} className="text-purple-400" /> Highest Credibility
                  </h4>
                  <div className="space-y-2">
                    {topCandidates.highest_credibility?.map((c, i) => (
                      <div key={i} className="flex items-center justify-between text-xs py-1.5 border-b border-border-hover-custom last:border-0">
                        <span className="text-txt-primary">#{i + 1} {c.candidate_name}</span>
                        <span className="font-bold" style={{ color: scoreColor(c.credibility_score) }}>{c.credibility_score}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
                  <h4 className="text-sm font-semibold text-txt-primary mb-3 flex items-center gap-2">
                    <TrendingUp size={14} className="text-blue-400" /> Highest Interview Score
                  </h4>
                  <div className="space-y-2">
                    {topCandidates.highest_interview_score?.map((c, i) => (
                      <div key={i} className="flex items-center justify-between text-xs py-1.5 border-b border-border-hover-custom last:border-0">
                        <span className="text-txt-primary">#{i + 1} {c.candidate_name}</span>
                        <span className="font-bold" style={{ color: scoreColor(c.interview_score) }}>{c.interview_score}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Score distribution */}
              {topCandidates.top_10?.length > 0 && (
                <div className="bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
                  <h4 className="text-sm font-semibold text-txt-primary mb-3 flex items-center gap-2">
                    <BarChart3 size={14} className="text-brand-indigo" /> Top 10 — Score Trend
                  </h4>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={topCandidates.top_10.map((c, i) => ({ rank: `#${i + 1}`, ...c, name: c.candidate_name }))} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2A3F5F" />
                        <XAxis dataKey="name" tick={{ fill: '#94A3B8', fontSize: 10 }} angle={-20} textAnchor="end" height={60} />
                        <YAxis domain={[0, 100]} tick={{ fill: '#94A3B8', fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: '#1A2236', border: '1px solid #2A3F5F', borderRadius: 8, fontSize: 12 }} />
                        <Legend wrapperStyle={{ fontSize: 11, color: '#94A3B8' }} />
                        <Line type="monotone" dataKey="hiring_score" name="Hiring Score" stroke="#10B981" strokeWidth={2} dot={{ r: 4, fill: '#10B981' }} />
                        <Line type="monotone" dataKey="resume_score" name="Resume Score" stroke="#3B82F6" strokeWidth={1.5} dot={{ r: 3, fill: '#3B82F6' }} strokeDasharray="4 2" />
                        <Line type="monotone" dataKey="interview_score" name="Interview Score" stroke="#F59E0B" strokeWidth={1.5} dot={{ r: 3, fill: '#F59E0B' }} strokeDasharray="4 2" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── COMPARE TAB ── */}
      {activeTab === 'compare' && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Candidate selection */}
          <div className="bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
            <h3 className="font-semibold text-txt-primary mb-3 flex items-center gap-2">
              <Users size={16} className="text-brand-indigo" />
              Select Candidates (min 2)
            </h3>
            <div className="space-y-1 max-h-80 overflow-y-auto">
              {leaderboard.map(c => (
                <label key={c.candidate_id}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                    compareIds.includes(c.candidate_id) ? 'bg-brand-indigo/10 text-brand-indigo' : 'text-txt-secondary hover:bg-bg-page/40'
                  }`}>
                  <input type="checkbox" checked={compareIds.includes(c.candidate_id)}
                    onChange={() => toggleCompareId(c.candidate_id)} className="accent-brand-indigo" />
                  {c.candidate_name}
                  <span className="ml-auto text-[10px] text-txt-tertiary">{c.hiring_score}</span>
                </label>
              ))}
            </div>
            <button onClick={handleCompare} disabled={compareIds.length < 2 || compareLoading}
              className="mt-3 w-full py-2 bg-brand-indigo text-white rounded-lg text-xs font-medium hover:bg-brand-indigo/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5">
              {compareLoading ? 'Comparing...' : `Compare (${compareIds.length})`}
            </button>
          </div>

          {/* Comparison results */}
          <div className="xl:col-span-2 bg-bg-elevated rounded-xl border border-border-hover-custom p-4">
            {!comparisonData ? (
              <div className="p-8 text-center text-txt-tertiary">
                <Users size={32} className="mx-auto mb-3 opacity-40" />
                <p className="text-sm">Select two or more candidates and click Compare</p>
              </div>
            ) : compareLoading ? (
              <div className="p-8 text-center text-txt-tertiary">Loading comparison...</div>
            ) : (
              <div className="space-y-4">
                <h3 className="font-semibold text-txt-primary">Candidate Comparison</h3>

                {/* Score comparison bars */}
                <div className="bg-bg-page/50 rounded-lg p-4 border border-border-hover-custom">
                  <h4 className="text-xs font-semibold text-txt-secondary uppercase tracking-wider mb-3">Score Comparison</h4>
                  <div className="space-y-3">
                    {['resume_score', 'interview_score', 'credibility_score', 'hiring_score'].map(metric => (
                      <div key={metric}>
                        <p className="text-[11px] text-txt-tertiary mb-1 capitalize">{metric.replace('_', ' ')}</p>
                        <div className="flex gap-4">
                          {comparisonData.map((c, i) => (
                            <div key={i} className="flex-1">
                              <div className="flex justify-between text-[10px] text-txt-secondary mb-0.5">
                                <span>{c.candidate_name}</span>
                                <span className="font-bold">{c[metric] || 0}</span>
                              </div>
                              <div className="h-2 bg-bg-page rounded-full overflow-hidden">
                                <div className="h-full rounded-full transition-all" style={{
                                  width: `${Math.min(c[metric] || 0, 100)}%`,
                                  backgroundColor: [ '#3B82F6', '#10B981', '#8B5CF6', '#F59E0B' ][i % 4],
                                }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Side-by-side details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {comparisonData.map((c, i) => (
                    <div key={i} className="bg-bg-page/30 rounded-lg p-3 border border-border-hover-custom">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium text-txt-primary text-sm">{c.candidate_name}</h5>
                        <RecommendationBadge rec={c.recommendation} />
                      </div>

                      {(c.strengths || []).length > 0 && (
                        <div className="mb-2">
                          <p className="text-[10px] text-green-400 font-medium mb-1">Strengths</p>
                          <div className="flex flex-wrap gap-1">
                            {c.strengths.slice(0, 4).map((s, j) => (
                              <Pill key={j} label={typeof s === 'string' ? s : s.name || s.skill || ''} color="green" />
                            ))}
                          </div>
                        </div>
                      )}

                      {(c.weaknesses || []).length > 0 && (
                        <div className="mb-2">
                          <p className="text-[10px] text-red-400 font-medium mb-1">Concerns</p>
                          <div className="flex flex-wrap gap-1">
                            {c.weaknesses.slice(0, 3).map((w, j) => (
                              <Pill key={j} label={typeof w === 'string' ? w : w.name || w.skill || ''} color="red" />
                            ))}
                          </div>
                        </div>
                      )}

                      <p className="text-[10px] text-txt-tertiary">Sessions: {c.session_count || 0}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
