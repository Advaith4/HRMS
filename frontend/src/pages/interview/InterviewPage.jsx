import { useState, useEffect, useCallback } from 'react'
import { abandonSession, startInterviewForApplication } from '../../api/interview'
import { getCandidateDashboardData } from '../../api'
import InterviewWorkspace from '../../components/interview/InterviewWorkspace'
import { Briefcase, AlertTriangle, Shield, CheckCircle, Clock, ArrowRight } from 'lucide-react'
import toast from 'react-hot-toast'

export default function InterviewPage() {
  const [session, setSession] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [applications, setApplications] = useState([])
  const [loadingApps, setLoadingApps] = useState(false)

  const handleStartForApplication = async (appId) => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await startInterviewForApplication(appId)
      setSession(data)
      const url = new URL(window.location)
      url.searchParams.set('appId', appId)
      window.history.pushState({}, '', url)
      toast.success('Interview started!')
    } catch (err) {
      console.error('Failed to start interview:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to start interview')
      toast.error('Failed to start interview')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchCandidateApplications = async () => {
    setLoadingApps(true)
    try {
      const data = await getCandidateDashboardData()
      setApplications(data.applications || [])
    } catch (err) {
      console.error('Failed to fetch applications:', err)
      toast.error('Failed to load active applications.')
    } finally {
      setLoadingApps(false)
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const appId = params.get('appId')
    if (appId) {
      handleStartForApplication(appId)
    } else {
      fetchCandidateApplications()
    }
  }, [])

  useEffect(() => {
    if (!session) return
    const handler = (e) => {
      e.preventDefault()
      e.returnValue = 'Interview in progress. Are you sure you want to leave?'
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [session])

  const handleEnd = useCallback(async () => {
    if (window.confirm('Interview in progress. Are you sure you want to leave?')) {
      if (session?.session_id && session.status === 'active') {
        try {
          await abandonSession(session.session_id)
        } catch (err) {
          console.error('Failed to abandon interview:', err)
        }
      }
      setSession(null)
      const url = new URL(window.location)
      url.searchParams.delete('appId')
      window.history.pushState({}, '', url)
      window.location.href = '/dashboard/candidate'
    }
  }, [session])

  if (session) {
    return (
      <div className="h-full min-h-0 bg-gray-50">
        <InterviewWorkspace session={session} onEnd={handleEnd} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="max-w-4xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="border-b border-gray-200 pb-3 sm:pb-4">
          <h1 className="text-xl sm:text-3xl font-extrabold text-gray-950 flex items-center gap-2">
            <Shield className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600 shrink-0" />
            AI Interview Portal
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">
            Standardized, secure proctored job interviews. Complete your interview to finalize your application.
          </p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-xs font-bold underline hover:text-red-900">
              Dismiss
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-3 bg-white rounded-2xl border border-gray-200 shadow-sm">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm font-semibold text-gray-600">Initializing secure proctored environment...</p>
          </div>
        ) : loadingApps ? (
          <div className="space-y-4">
            <div className="h-24 bg-gray-200 rounded-xl animate-pulse" />
            <div className="h-24 bg-gray-200 rounded-xl animate-pulse" />
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-gray-100 bg-gray-50/50">
              <h2 className="text-base font-bold text-gray-900">Your Active Applications</h2>
              <p className="text-xs text-gray-500 mt-0.5">Below is the status of AI interviews linked to your applications.</p>
            </div>

            {applications.length === 0 ? (
              <div className="p-12 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto text-gray-400">
                  <Briefcase size={20} />
                </div>
                <h3 className="text-sm font-bold text-gray-900">No active applications found</h3>
                <p className="text-xs text-gray-500 max-w-xs mx-auto">
                  You haven't applied to any job vacancies yet. Apply for a career vacancy first to start the mandatory interview.
                </p>
                <a
                  href="/jobs"
                  className="inline-block bg-blue-600 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Browse Career Board
                </a>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {applications.map((app) => (
                  <div key={app.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-gray-900 leading-snug">{app.job_title}</div>
                      <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-1 flex-wrap">
                        <span className="text-[10px] text-gray-400 font-mono">ID {app.id}</span>
                        <span className="text-gray-300">•</span>
                        <span>Applied {new Date(app.application_date).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {/* Interview status badge */}
                      {app.can_start_interview && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-full uppercase tracking-wider">
                            <Clock className="w-3 h-3" />
                            Pending
                          </span>
                          <button
                            onClick={() => handleStartForApplication(app.id)}
                            className="inline-flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white text-[11px] sm:text-xs font-bold px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg transition-colors cursor-pointer shadow-sm"
                          >
                            <span>Start Interview</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                      {app.can_resume_interview && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-bold text-brand-indigo bg-brand-indigo/10 border border-brand-indigo/20 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-full uppercase tracking-wider">
                            <Clock className="w-3 h-3" />
                            Active
                          </span>
                          <button
                            onClick={() => handleStartForApplication(app.id)}
                            className="inline-flex items-center gap-1 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-[11px] sm:text-xs font-bold px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg transition-colors cursor-pointer shadow-sm"
                          >
                            <span>Resume Interview</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                      {app.interview_completed && (
                        <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-bold text-green-700 bg-green-50 border border-green-200 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-full uppercase tracking-wider">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Completed {app.interview_score !== null && `(${app.interview_score.toFixed(1)}/10)`}
                        </span>
                      )}
                      {app.interview_analyzing && (
                        <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-full uppercase tracking-wider">
                          <Clock className="w-3.5 h-3.5" />
                          Analyzing
                        </span>
                      )}
                      {app.interview_status === 'cancelled' && (
                        <span className="inline-flex items-center gap-1 text-[11px] sm:text-xs font-bold text-red-700 bg-red-50 border border-red-200 px-2.5 py-0.5 sm:px-3 sm:py-1 rounded-full uppercase tracking-wider">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Cancelled
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
