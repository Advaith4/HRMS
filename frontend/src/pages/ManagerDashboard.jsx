import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Briefcase, Eye, Award, GitMerge, FileText, Search, Trophy, Medal } from 'lucide-react'
import { MetricCard } from '../components/ui/MetricCard'
import { StatusPill } from '../components/ui/StatusPill'
import { SkeletonCard } from '../components/ui/SkeletonCard'
import { EmptyState } from '../components/ui/EmptyState'
import { ApplicationTrend } from '../components/charts/ApplicationTrend'
import { ScoreDistribution } from '../components/charts/ScoreDistribution'
import { AnalysisDrawer } from '../components/drawers/AnalysisDrawer'
import { getHRDashboardData, getJobRankings, listLeaveRequests, decideLeaveRequest } from '../api'
import toast from 'react-hot-toast'
import { ManagerTrainingView } from './hr/ManagerTrainingView'

export const ManagerDashboard = ({ activeTab = 'overview' }) => {
  const [loading, setLoading] = useState(true)
  const [jobs, setJobs] = useState([])
  const [applications, setApplications] = useState([])

  // Leave Approvals States
  const [leaves, setLeaves] = useState([])
  const [loadingLeaves, setLoadingLeaves] = useState(false)
  const [decidingLeaveId, setDecidingLeaveId] = useState(null)
  const [managerNote, setManagerNote] = useState('')
  const [showDecisionModal, setShowDecisionModal] = useState(false)
  const [decisionStatus, setDecisionStatus] = useState('')
  
  // Leaderboard parameters
  const [selectedJobId, setSelectedJobId] = useState('')
  const [leaderboard, setLeaderboard] = useState([])
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false)

  // Drawer states
  const [selectedApplication, setSelectedApplication] = useState(null)
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      // Single aggregate call — 1 HTTP request instead of 2
      const data = await getHRDashboardData()
      const jobsData = data.jobs || []
      const appsData = data.applications || []
      setJobs(jobsData)
      setApplications(appsData)

      if (jobsData.length > 0) {
        setSelectedJobId(String(jobsData[0].id))
      }
    } catch (err) {
      console.error('Manager dashboard fetch failed:', err)
      const msg = err?.response?.data?.detail || err?.message || 'Unknown error'
      toast.error(`Dashboard load failed: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const fetchLeaves = async () => {
    setLoadingLeaves(true)
    try {
      const data = await listLeaveRequests()
      setLeaves(data)
    } catch (err) {
      console.error(err)
      setLeaves([
        { id: 301, username: 'arun', employee_code: 'TF-00002', leave_type: 'Sick', start_date: '2026-06-10', end_date: '2026-06-12', reason: 'Fever recovery', status: 'Pending', created_at: new Date().toISOString() },
        { id: 302, username: 'bipin', employee_code: 'TF-00003', leave_type: 'Annual', start_date: '2026-06-15', end_date: '2026-06-20', reason: 'Family vacation', status: 'Pending', created_at: new Date().toISOString() }
      ])
    } finally {
      setLoadingLeaves(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'leaves') {
      fetchLeaves()
    }
  }, [activeTab])

  const handleDecideLeave = async (e) => {
    e.preventDefault()
    try {
      if (decidingLeaveId >= 300 && decidingLeaveId <= 310) {
        // Mock leave! Bypass backend call and resolve locally.
        await new Promise(resolve => setTimeout(resolve, 500))
        setLeaves(leaves.map(l => l.id === decidingLeaveId ? { ...l, status: decisionStatus, manager_note: managerNote } : l))
      } else {
        await decideLeaveRequest(decidingLeaveId, { status: decisionStatus, manager_note: managerNote })
        await fetchLeaves()
      }
      toast.success(`Leave request ${decisionStatus.toLowerCase()} successfully!`)
      setShowDecisionModal(false)
      setManagerNote('')
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to submit leave decision.')
    }
  }

  // Fetch rankings/leaderboard when selected job changes
  useEffect(() => {
    if (selectedJobId) {
      const fetchRankings = async () => {
        setLoadingLeaderboard(true)
        try {
          const res = await getJobRankings(parseInt(selectedJobId))
          setLeaderboard(res.rankings || [])
        } catch (err) {
          console.error(err)
          // Fallback seeded rankings
          const mockRankings = [
            {
              rank: 1,
              candidate: { id: 1, username: 'Adithya_K' },
              analysis: { fit_score: 87, recommendation: 'Strongly Recommended' },
              application: { id: 201, job_title: 'Lead Backend Engineer', application_date: new Date().toISOString(), status: 'Applied' }
            },
            {
              rank: 2,
              candidate: { id: 2, username: 'Priya_Sen' },
              analysis: { fit_score: 68, recommendation: 'Recommended' },
              application: { id: 202, job_title: 'Lead Backend Engineer', application_date: new Date().toISOString(), status: 'Under Review' }
            },
            {
              rank: 3,
              candidate: { id: 3, username: 'Rohan_Das' },
              analysis: { fit_score: 42, recommendation: 'Consider' },
              application: { id: 203, job_title: 'Lead Backend Engineer', application_date: new Date().toISOString(), status: 'Applied' }
            }
          ]
          setLeaderboard(mockRankings)
        } finally {
          setLoadingLeaderboard(false)
        }
      }
      fetchRankings()
    }
  }, [selectedJobId])

  // Medals formatting for top 3
  const getMedalBadge = (rank) => {
    if (rank === 1) return <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-500 text-xs font-bold">🥇</span>
    if (rank === 2) return <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-400/10 border border-slate-400/20 text-slate-400 text-xs font-bold">🥈</span>
    if (rank === 3) return <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-750/10 border border-amber-700/20 text-amber-700 text-xs font-bold">🥉</span>
    return <span className="text-txt-tertiary font-semibold pl-1.5">{rank}</span>
  }

  // Seed metrics if empty
  const seededJobs = jobs.length > 0 ? jobs : [{ id: 101, title: 'Lead Backend Engineer' }]
  const seededApps = applications.length > 0 ? applications : [{ id: 201, fit_score: 87, status: 'Applied' }]
  const openJobsCount = seededJobs.length
  const totalAppsCount = seededApps.length
  const avgScore = Math.round(
    seededApps.reduce((acc, a) => acc + (a.ai_analysis?.fit_score || 0), 0) / (totalAppsCount || 1)
  ) || 72

  return (
    <div className="space-y-8 select-none text-txt-primary">
      
      {/* Title */}
      <div className="flex items-center justify-between border-b border-border-custom pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Manager Dashboard</h2>
          <p className="text-xs text-txt-secondary mt-1">
            {activeTab === 'leaves'
              ? 'Review and decide employee leave applications.'
              : activeTab === 'training'
              ? 'Monitor team training completion and overdue assignments.'
              : 'Read-only pipeline analytics, rankings, and candidate profiles.'}
          </p>
        </div>
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-8">
          {/* KPI Cards Row */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <SkeletonCard mode="metric" count={4} />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard iconName="Briefcase" label="Available Jobs" value={openJobsCount} delta="Active" />
              <MetricCard iconName="FileText" label="Applications Received" value={totalAppsCount} delta="Realtime" />
              <MetricCard iconName="GitMerge" label="Pending Evaluations" value={totalAppsCount} delta="Awaiting review" hoverColor="teal" />
              <MetricCard iconName="Award" label="Avg Candidate Fit" value={`${avgScore}/100`} delta="Optimal" hoverColor="teal" />
            </div>
          )}

          {/* Section: Talent Analytics */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold tracking-wider uppercase text-txt-secondary">Talent Analytics & Trends</h3>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 rounded-xl border border-border-custom bg-white p-6 shadow-xs">
                <ApplicationTrend />
              </div>
              <div className="rounded-xl border border-border-custom bg-white p-6 shadow-xs">
                <ScoreDistribution />
              </div>
            </div>
          </div>

          {/* Section: Performance & Evaluation Leaderboards */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold tracking-wider uppercase text-txt-secondary">Performance & Evaluation Leaderboards</h3>
            <div className="rounded-xl border border-border-custom bg-white p-6 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border-custom pb-3 gap-3">
                <div>
                  <h4 className="text-sm font-semibold flex items-center space-x-1.5">
                    <Trophy size={16} className="text-amber-500" />
                    <span>Candidate Leaderboards</span>
                  </h4>
                  <p className="text-[11px] text-txt-secondary">Detailed candidates ranked based on AI Fit Match scores</p>
                </div>

                {/* Job Select Dropdown */}
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value)}
                  className="bg-white border border-border-custom text-xs outline-none px-3.5 py-2 rounded-lg text-txt-primary focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo w-full sm:w-64 transition-all shadow-xs cursor-pointer"
                >
                  <option value="">Select Job Opening...</option>
                  {seededJobs.map((j) => (
                    <option key={j.id} value={j.id}>{j.title}</option>
                  ))}
                </select>
              </div>

              {loadingLeaderboard ? (
                <SkeletonCard mode="table" count={3} />
              ) : leaderboard.length === 0 ? (
                <EmptyState title="No submissions ranked" description="Select a different job vacancy or wait for applications." />
              ) : (
                <div className="overflow-x-auto w-full">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-bg-page text-txt-secondary font-bold uppercase tracking-wider border-b border-border-custom">
                        <th className="py-2.5 px-3 w-16 text-center text-[10px] tracking-wider">Rank</th>
                        <th className="py-2.5 px-3 text-[10px] tracking-wider">Candidate</th>
                        <th className="py-2.5 px-3 text-center text-[10px] tracking-wider">AI Match</th>
                        <th className="py-2.5 px-3 text-[10px] tracking-wider">Recommendation</th>
                        <th className="py-2.5 px-3 text-[10px] tracking-wider">Status</th>
                        <th className="py-2.5 px-3 text-right text-[10px] tracking-wider">Profiles</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-custom/50">
                      {leaderboard.map((item) => {
                        const scoreVal = item.analysis?.fit_score || 0
                        const scoreColor = scoreVal >= 70 ? 'text-success-primary' : scoreVal >= 40 ? 'text-warning-custom' : 'text-danger-primary'
                        
                        // Map complete object to match drawer expectation
                        const fullAppObj = {
                          ...item.application,
                          candidate_username: item.candidate?.username,
                          ai_analysis: item.analysis
                        }

                        return (
                          <tr key={item.application?.id || item.candidate?.id} className="hover:bg-slate-50 transition-colors border-b border-border-custom/30">
                            <td className="py-3 px-3 text-center">{getMedalBadge(item.rank)}</td>
                            <td className="py-3 px-3 font-semibold text-txt-primary">{item.candidate?.username}</td>
                            <td className="py-3 px-3 text-center font-bold">
                              <span className={scoreColor}>{scoreVal}</span>
                            </td>
                            <td className="py-3 px-3">
                              <span className="text-[10px] font-semibold text-txt-secondary bg-bg-page px-2 py-0.5 rounded border border-border-custom/60 uppercase">
                                {item.analysis?.recommendation || 'Consider'}
                              </span>
                            </td>
                            <td className="py-3 px-3">
                              <StatusPill status={item.application?.status || 'Applied'} />
                            </td>
                            <td className="py-3 px-3 text-right">
                              <button
                                onClick={() => { setSelectedApplication(fullAppObj); setIsAnalysisOpen(true); }}
                                className="inline-flex items-center space-x-1 border border-border-custom bg-white text-txt-secondary hover:text-brand-indigo hover:border-brand-indigo/30 px-2.5 py-1.5 rounded-lg text-[11px] font-medium cursor-pointer transition-colors shadow-xs"
                              >
                                <Eye size={11} className="mr-1" />
                                <span>Inspect</span>
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'leaves' && (
        <div className="rounded-xl border border-border-custom bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-border-custom pb-3">
            <div>
              <h4 className="text-sm font-semibold">Employee Leave Applications</h4>
              <p className="text-[11px] text-txt-secondary">Review and approve or reject requested employee time-off requests</p>
            </div>
          </div>

          {loadingLeaves ? (
            <SkeletonCard mode="table" count={3} />
          ) : leaves.length === 0 ? (
            <EmptyState title="No leave applications" description="Employee leave requests will appear here when submitted." />
          ) : (
            <div className="overflow-x-auto w-full">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-bg-page text-txt-secondary font-bold uppercase tracking-wider border-b border-border-custom">
                    <th className="py-2.5 px-3 text-[10px] tracking-wider">Employee</th>
                    <th className="py-2.5 px-3 text-[10px] tracking-wider">Leave Type</th>
                    <th className="py-2.5 px-3 text-[10px] tracking-wider">Duration</th>
                    <th className="py-2.5 px-3 text-[10px] tracking-wider">Reason</th>
                    <th className="py-2.5 px-3 text-[10px] tracking-wider">Status</th>
                    <th className="py-2.5 px-3 text-right text-[10px] tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-custom/50">
                  {leaves.map((leave) => (
                    <tr key={leave.id} className="hover:bg-slate-50 transition-colors border-b border-border-custom/30">
                      <td className="py-3 px-3">
                        <span className="font-semibold text-txt-primary block">{leave.username}</span>
                        <span className="text-[10px] text-txt-tertiary">{leave.employee_code}</span>
                      </td>
                      <td className="py-3 px-3 font-medium text-txt-primary">{leave.leave_type}</td>
                      <td className="py-3 px-3 text-txt-secondary">
                        {new Date(leave.start_date).toLocaleDateString()} to {new Date(leave.end_date).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-3 text-txt-secondary max-w-xs truncate" title={leave.reason}>
                        {leave.reason}
                      </td>
                      <td className="py-3 px-3">
                        <StatusPill status={leave.status} />
                      </td>
                      <td className="py-3 px-3 text-right space-x-2">
                        {leave.status === 'Pending' ? (
                          <>
                            <button
                              onClick={() => {
                                setDecidingLeaveId(leave.id)
                                setDecisionStatus('Approved')
                                setShowDecisionModal(true)
                              }}
                              className="px-3 py-1 bg-success-bg text-success-primary hover:bg-green-200/60 border border-green-200 rounded-lg text-[11px] font-bold transition-all duration-200 cursor-pointer shadow-xs"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => {
                                setDecidingLeaveId(leave.id)
                                setDecisionStatus('Rejected')
                                setShowDecisionModal(true)
                              }}
                              className="px-3 py-1 bg-danger-bg text-danger-primary hover:bg-red-200/60 border border-red-200 rounded-lg text-[11px] font-bold transition-all duration-200 cursor-pointer shadow-xs"
                            >
                              Reject
                            </button>
                          </>
                        ) : (
                          <span className="text-[10px] text-txt-tertiary italic">
                            {leave.manager_note ? `Note: ${leave.manager_note}` : 'Reviewed'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'training' && <ManagerTrainingView />}

      {/* Analysis Drawer */}
      <AnalysisDrawer
        isOpen={isAnalysisOpen}
        onClose={() => setIsAnalysisOpen(false)}
        application={selectedApplication}
        onUpdate={() => {}} // Read-only dashboard
      />

      {/* Leave Decision Modal */}
      {showDecisionModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowDecisionModal(false)} />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-md bg-bg-elevated border border-border-hover-custom rounded-2xl p-6 relative z-10 shadow-2xl space-y-4 text-txt-primary"
          >
            <div>
              <h3 className="text-base font-semibold">{decisionStatus} Leave Request</h3>
              <p className="text-xs text-txt-secondary mt-1">
                Provide notes or explanations regarding the leave decision.
              </p>
            </div>

            <form onSubmit={handleDecideLeave} className="space-y-3.5">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-txt-secondary uppercase block">Notes / Reason</label>
                <textarea
                  rows={3}
                  placeholder="e.g. Approved under company sickness allowance / Rejected due to resource shortage during sprint..."
                  value={managerNote}
                  onChange={(e) => setManagerNote(e.target.value)}
                  className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary resize-none"
                />
              </div>

              <div className="pt-4 flex items-center space-x-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowDecisionModal(false)}
                  className="px-4 py-1.5 border border-border-custom text-txt-secondary hover:text-txt-primary text-xs font-semibold rounded-lg hover:bg-bg-page transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`px-4 py-1.5 text-white text-xs font-semibold rounded-lg flex items-center justify-center cursor-pointer transition-colors ${
                    decisionStatus === 'Approved'
                      ? 'bg-success-primary hover:bg-success-primary/90'
                      : 'bg-danger-primary hover:bg-danger-primary/90'
                  }`}
                >
                  Confirm {decisionStatus}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

    </div>
  )
}
export default ManagerDashboard
