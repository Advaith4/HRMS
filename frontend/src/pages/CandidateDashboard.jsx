import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Briefcase, FileText, Search, Clock, CheckCircle, ChevronDown, ChevronUp, Eye, Layout, SlidersHorizontal } from 'lucide-react'
import { MetricCard } from '../components/ui/MetricCard'
import { StatusPill } from '../components/ui/StatusPill'
import { SkeletonCard } from '../components/ui/SkeletonCard'
import { EmptyState } from '../components/ui/EmptyState'
import { JobDetailDrawer } from '../components/drawers/JobDetailDrawer'
import { ProfileSetupWizard } from '../components/ProfileSetupWizard'
import { ProfileCompletionWidget } from '../components/ProfileCompletionWidget'
import { getCandidateDashboardData, getMyProfileCompletion, invalidateCache } from '../api'
import toast from 'react-hot-toast'

export const CandidateDashboard = ({ activeTab = 'overview' }) => {
  const [loading, setLoading] = useState(true)
  const [jobs, setJobs] = useState([])
  const [applications, setApplications] = useState([])
  const [hasResume, setHasResume] = useState(false)
  const [resumeData, setResumeData] = useState(null)
  const [profileComplete, setProfileComplete] = useState(null)
  const [profileCompletion, setProfileCompletion] = useState(null)

  // Drawer Trigger
  const [selectedJob, setSelectedJob] = useState(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('All')
  const [showFilters, setShowFilters] = useState(false)

  // Accordion rows tracking
  const [expandedRow, setExpandedRow] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [data, profileData] = await Promise.all([
        getCandidateDashboardData(),
        getMyProfileCompletion(),
      ])
      setJobs(data.jobs || [])
      setApplications(data.applications || [])
      setHasResume(data.has_resume || false)
      if (data.resume) setResumeData(data.resume)
      setProfileCompletion(profileData.profile || profileData)
      setProfileComplete(!!profileData.profile?.is_complete)
    } catch (err) {
      console.error('Candidate dashboard fetch failed:', err)
      const msg = err?.response?.data?.detail || err?.message || 'Unknown error'
      toast.error(`Dashboard load failed: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleApplySuccess = (newApp) => {
    setApplications(prev => [newApp, ...prev])
    setIsDetailOpen(false)
    // Invalidate cache so next open shows fresh data
    invalidateCache('/api/dashboard/candidate')
  }

  const seededJobs = jobs
  const seededApplications = applications

  const availableJobsCount = seededJobs.length
  const appsSubmittedCount = seededApplications.length
  const pendingAppsCount = seededApplications.filter(a => a.status === 'Applied' || a.status === 'Under Review').length
  const acceptedAppsCount = seededApplications.filter(a => a.status === 'Hired').length

  // Filter Jobs list
  const filteredJobs = seededJobs.filter(job => {
    const query = searchQuery.toLowerCase().trim()
    const matchesSearch =
      job.title.toLowerCase().includes(query) ||
      job.department.toLowerCase().includes(query) ||
      (job.required_skills || '').toLowerCase().includes(query)

    if (departmentFilter === 'All') return matchesSearch
    return matchesSearch && job.department.toLowerCase() === departmentFilter.toLowerCase()
  })

  // List unique departments for filter chips
  const departments = ['All', ...new Set(seededJobs.map(j => j.department))]

  if (profileComplete === false) {
    return <ProfileSetupWizard role="candidate" onComplete={() => { setProfileComplete(true); fetchData(); }} />
  }

  return (
    <div className="space-y-8 select-none text-txt-primary">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-custom pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Careers Portal</h2>
          <p className="text-xs text-txt-secondary mt-1">Browse active vacancies, apply with your resume, and check AI feedback.</p>
        </div>
      </div>

      {/* Metrics Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <SkeletonCard mode="metric" count={4} />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard iconName="Briefcase" label="Available Careers" value={availableJobsCount} delta="Active" />
          <MetricCard iconName="FileText" label="Applications Submitted" value={appsSubmittedCount} delta="Realtime tracking" />
          <MetricCard iconName="Clock" label="Pending Evaluations" value={pendingAppsCount} delta="Avg 48h response" hoverColor="teal" />
          <MetricCard iconName="CheckCircle" label="Hired Profiles" value={acceptedAppsCount} delta="Congrats!" hoverColor="teal" />
        </div>
      )}

      {/* OVERVIEW / HOME FEED TAB */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left/Middle Column (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Welcome banner */}
            <div className="relative rounded-2xl bg-white border border-border-custom p-8 overflow-hidden shadow-xs">
              <div className="space-y-4 max-w-xl z-10 relative">
                <span className="text-[10px] font-bold tracking-wider text-brand-indigo bg-brand-indigo-muted/50 border border-brand-indigo/10 px-2.5 py-1 rounded-md uppercase">
                  Careers Portal
                </span>
                <h3 className="text-xl font-bold tracking-tight text-txt-primary">
                  Accelerate Your Career with Secure Matching
                </h3>
                <p className="text-xs text-txt-secondary leading-relaxed max-w-lg">
                  Upload your professional PDF resume to match with open positions, and review suitability metrics, strengths/weaknesses highlights, and curated interview preparations.
                </p>
                <div className="pt-2">
                  <Link
                    to="/jobs"
                    className="inline-flex items-center px-4 py-2 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold rounded-lg transition-all cursor-pointer shadow-xs active:scale-[0.98]"
                  >
                    <span>Browse Careers</span>
                    <Briefcase size={14} className="ml-1.5" />
                  </Link>
                </div>
              </div>
            </div>

            {/* Recommended/Latest Vacancies */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold tracking-wider uppercase text-txt-secondary">Recommended Vacancies</h4>
                <Link to="/jobs" className="text-[10px] font-semibold text-brand-indigo hover:underline">View all</Link>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {seededJobs.slice(0, 2).map((job) => {
                  return (
                    <div key={job.id} className="bg-white border border-border-custom p-5 rounded-xl flex flex-col justify-between space-y-3 shadow-xs hover:shadow-sm hover:border-border-hover-custom transition-all">
                      <div>
                        <span className="text-xs font-bold text-txt-primary block leading-none">{job.title}</span>
                        <span className="text-[9px] text-txt-tertiary mt-1.5 block leading-none">{job.department}</span>
                        <p className="text-[11px] text-txt-secondary mt-2.5 line-clamp-2 leading-relaxed">
                          {job.description}
                        </p>
                      </div>
                      <div className="flex items-center justify-between pt-2 border-t border-border-custom/50">
                        <span className="text-[10px] text-brand-indigo font-bold">{job.salary_range}</span>
                        <button
                          onClick={() => { setSelectedJob(job); setIsDetailOpen(true); }}
                          className="px-3 py-1.5 bg-brand-indigo/10 hover:bg-brand-indigo/25 text-brand-indigo border border-brand-indigo/20 text-[10px] font-bold rounded-lg cursor-pointer transition-colors shadow-xs"
                        >
                          Details
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

          </div>

          {/* Right Column (1/3 width) */}
          <div className="space-y-6">
            
            {/* Profile Completion Card */}
            {profileCompletion && (
              <ProfileCompletionWidget
                profileCompletion={profileCompletion}
                onAction={() => setProfileComplete(false)}
              />
            )}

            {/* Resume Status Card */}
            <div className="bg-white border border-border-custom rounded-xl p-5 space-y-4 shadow-xs">
              <span className="text-[9px] font-bold tracking-wider uppercase text-txt-secondary block">My Resume Status</span>
              {hasResume ? (
                <div className="flex items-center space-x-3 p-3.5 bg-slate-50 border border-border-custom rounded-lg">
                  <div className="p-2 rounded-md bg-success-bg text-success-primary">
                    <FileText size={15} />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-txt-primary block">Resume Active</span>
                    <span className="text-[9px] text-txt-secondary mt-0.5 block">Uploaded and verified successfully</span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center space-x-3 p-3.5 bg-slate-50 border border-border-custom rounded-lg">
                  <div className="p-2 rounded-md bg-warning-bg text-warning-primary">
                    <Clock size={15} />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-txt-primary block">No Active Resume</span>
                    <span className="text-[9px] text-txt-secondary mt-0.5 block">Required to submit application</span>
                  </div>
                </div>
              )}
            </div>

            {/* Application Progress Status */}
            <div className="bg-white border border-border-custom rounded-xl p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-bold tracking-wider uppercase text-txt-secondary">My Applications</span>
                <Link to="/applications" className="text-[10px] font-semibold text-brand-indigo hover:underline">All applications</Link>
              </div>

              {seededApplications.length === 0 ? (
                <p className="text-[10px] text-txt-secondary italic">No applications submitted yet.</p>
              ) : (
                <div className="space-y-3">
                  {seededApplications.slice(0, 3).map((app) => (
                    <div key={app.id} className="flex items-center justify-between p-2.5 rounded-lg border border-border-custom bg-slate-50/50">
                      <div>
                        <span className="text-[10px] font-bold text-txt-primary block">{app.job_title}</span>
                        <span className="text-[9px] text-txt-tertiary block mt-0.5">Applied {new Date(app.application_date).toLocaleDateString()}</span>
                      </div>
                      <StatusPill status={app.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

        </div>
      )}

      {/* OVERVIEW / SEARCH JOBS TAB */}
      {activeTab === 'jobs' && (
        <div className="space-y-6">
          
          {/* Filters Area */}
          <div className="bg-bg-surface border border-border-custom p-4 rounded-xl space-y-4">
            <div className="flex items-center justify-between space-x-4">
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="Filter vacancies by title, tech stack or keywords..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-4 py-2 pl-10 text-xs rounded-lg text-txt-primary"
                />
                <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-txt-tertiary" />
              </div>
              
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="h-8 border border-border-custom bg-bg-page px-3 rounded-lg text-xs flex items-center space-x-1.5 hover:text-txt-primary cursor-pointer text-txt-secondary"
              >
                <SlidersHorizontal size={13} />
                <span>Filters</span>
              </button>
            </div>

            {/* Department chips */}
            {(showFilters || departmentFilter !== 'All') && (
              <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border-custom/50">
                {departments.map((dept) => (
                  <button
                    key={dept}
                    onClick={() => setDepartmentFilter(dept)}
                    className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-colors cursor-pointer ${
                      departmentFilter === dept
                        ? 'bg-brand-indigo text-white'
                        : 'bg-bg-page border border-border-custom text-txt-secondary hover:text-txt-primary'
                    }`}
                  >
                    {dept}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Job Feed Grid (2 Cols) */}
          {filteredJobs.length === 0 ? (
            <EmptyState title="No careers found" description="Adjust your keyword filter query or department selection." />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {filteredJobs.map((job) => {
                const skills = (job.required_skills || '').split(/[,|;]+/).slice(0, 4)
                const alreadyApplied = seededApplications.some(a => a.job_title === job.title)

                return (
                  <motion.div
                    key={job.id}
                    whileHover={{ y: -2 }}
                    className="rounded-xl border border-border-custom bg-white p-6 flex flex-col justify-between space-y-4 shadow-xs hover:shadow-sm hover:border-brand-indigo/30 transition-all duration-300 relative group"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {/* Coloured Initials Placeholder avatar */}
                          <div className="w-8 h-8 rounded-lg bg-brand-indigo/10 border border-brand-indigo/20 flex items-center justify-center text-brand-indigo font-bold text-xs uppercase transition-colors group-hover:bg-brand-indigo group-hover:text-white">
                            {job.department.slice(0, 2)}
                          </div>
                          <div>
                            <span className="text-xs font-bold text-txt-primary block leading-none transition-colors group-hover:text-brand-indigo">{job.title}</span>
                            <span className="text-[9px] text-txt-tertiary mt-1.5 block leading-none">{job.department}</span>
                          </div>
                        </div>
                        {alreadyApplied && (
                          <span className="text-[9px] font-bold text-success-primary bg-success-bg border border-success-primary/20 px-2 py-0.5 rounded-full uppercase">
                            Applied
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-txt-secondary line-clamp-3 leading-relaxed">
                        {job.description}
                      </p>

                      {/* Skills pills */}
                      <div className="flex flex-wrap gap-1">
                        {skills.map((s, idx) => (
                          <span key={idx} className="text-[9px] bg-slate-50 border border-border-custom text-txt-secondary px-2 py-0.5 rounded-md">
                            {s.trim()}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-border-custom/50 flex items-center justify-between">
                      <div className="text-[10px] font-bold text-brand-indigo uppercase tracking-wider">
                        {job.salary_range || 'Competitive'}
                      </div>
                      
                      <button
                        onClick={() => { setSelectedJob(job); setIsDetailOpen(true); }}
                        className="px-3.5 py-1.5 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-[11px] font-semibold rounded-lg active:scale-98 transition-all cursor-pointer shadow-xs"
                      >
                        {alreadyApplied ? 'Inspect vacancy' : 'Apply now'}
                      </button>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}

        </div>
      )}

      {/* MY APPLICATIONS ACCORDION TAB */}
      {activeTab === 'applications' && (
        <div className="rounded-xl border border-border-custom bg-white p-6 shadow-xs space-y-4">
          <div className="border-b border-border-custom pb-3">
            <h4 className="text-sm font-semibold">Application History</h4>
            <p className="text-[11px] text-txt-secondary">Inspect resume analysis and selection stages</p>
          </div>

          {seededApplications.length === 0 ? (
            <EmptyState title="No application histories" description="Submit your resume to an active vacancy in the Career Boards." />
          ) : (
            <div className="w-full space-y-3">
              {seededApplications.map((app) => {
                const isExpanded = expandedRow === app.id
                const scoreVal = app.ai_analysis?.fit_score || 0
                const scoreColor = scoreVal >= 70 ? 'text-success-primary' : scoreVal >= 40 ? 'text-warning-custom' : 'text-danger-primary'

                return (
                  <div key={app.id} className="border border-border-custom rounded-xl bg-bg-page/20 overflow-hidden">
                    {/* Header Row */}
                    <div
                      onClick={() => setExpandedRow(isExpanded ? null : app.id)}
                      className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer hover:bg-bg-elevated/20 transition-colors select-none"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-lg bg-bg-page border border-border-custom text-brand-indigo">
                          <Briefcase size={16} />
                        </div>
                        <div>
                          <span className="text-xs font-bold text-txt-primary block">{app.job_title}</span>
                          <span className="text-[10px] text-txt-tertiary mt-1 block">
                            Applied on {new Date(app.application_date).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-4 self-end sm:self-auto">
                        <div className="flex items-center space-x-2 text-xs">
                          <span className="text-txt-tertiary font-medium">Fit Score:</span>
                          <span className={`font-bold ${scoreColor}`}>{scoreVal}/100</span>
                        </div>
                        <StatusPill status={app.status} />
                        
                        {isExpanded ? <ChevronUp size={16} className="text-txt-tertiary" /> : <ChevronDown size={16} className="text-txt-tertiary" />}
                      </div>
                    </div>

                    {/* Accordion Expand Area */}
                    <AnimatePresence>
                      {isExpanded && app.ai_analysis && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: 'auto' }}
                          exit={{ height: 0 }}
                          className="border-t border-border-custom bg-bg-page/40 overflow-hidden text-xs"
                        >
                          <div className="p-5 space-y-4">
                            
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                              {/* Left detail card */}
                              <div className="md:col-span-2 space-y-3">
                                <div>
                                  <span className="text-[9px] font-bold uppercase tracking-wider text-txt-tertiary block">AI Executive Summary</span>
                                  <p className="text-xs text-txt-secondary leading-relaxed mt-1">
                                    "{app.ai_analysis.summary}"
                                  </p>
                                </div>

                                <div className="grid grid-cols-2 gap-4 pt-2">
                                  {/* Strengths */}
                                  {app.ai_analysis.strengths?.length > 0 && (
                                    <div className="space-y-1.5">
                                      <span className="text-[9px] font-bold uppercase tracking-wider text-success-primary">Strengths</span>
                                      <div className="space-y-1">
                                        {app.ai_analysis.strengths.slice(0, 3).map((str, idx) => (
                                          <div key={idx} className="flex items-start space-x-1.5 text-txt-secondary">
                                            <span className="text-success-primary mt-0.5">✓</span>
                                            <span className="text-[10px]">{str}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  
                                  {/* Weaknesses */}
                                  {app.ai_analysis.weaknesses?.length > 0 && (
                                    <div className="space-y-1.5">
                                      <span className="text-[9px] font-bold uppercase tracking-wider text-danger-primary">Improvement Gaps</span>
                                      <div className="space-y-1">
                                        {app.ai_analysis.weaknesses.slice(0, 3).map((weak, idx) => (
                                          <div key={idx} className="flex items-start space-x-1.5 text-txt-secondary">
                                            <span className="text-danger-primary mt-0.5">✕</span>
                                            <span className="text-[10px]">{weak}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Right visual indicator */}
                              <div className="flex flex-col items-center justify-center p-4 bg-bg-surface/50 border border-border-custom rounded-xl">
                                <span className="text-[9px] font-bold uppercase text-txt-tertiary block mb-2">Recommendation Profile</span>
                                <div className="text-xs font-bold uppercase tracking-wider text-success-primary bg-success-bg px-4 py-1.5 rounded-full border border-success-primary/20">
                                  {app.ai_analysis.recommendation}
                                </div>
                                <span className="text-[9px] text-txt-tertiary mt-2 text-center max-w-[120px]">
                                  Ranked based on required job skills overlap.
                                </span>
                              </div>

                            </div>

                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                  </div>
                )
              })}
            </div>
          )}

        </div>
      )}

      {/* Drawer */}
      <JobDetailDrawer
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        job={selectedJob}
        onApplySuccess={handleApplySuccess}
      />

    </div>
  )
}
export default CandidateDashboard
