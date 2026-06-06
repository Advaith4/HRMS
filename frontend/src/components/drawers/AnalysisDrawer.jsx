import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Check, AlertTriangle, RefreshCw, Briefcase, Calendar, DollarSign, Award, Shield, HelpCircle } from 'lucide-react'
import { AIScoreDonut } from '../ui/AIScoreDonut'
import { StatusPill } from '../ui/StatusPill'

import {
  reanalyzeApplication,
  hireCandidate,
  listOnboardingTemplates
} from '../../api'

import { getApplicationCredibility } from '../../api/applications'

import { useAuthStore } from '../../store/authStore'
import toast from 'react-hot-toast'

export const AnalysisDrawer = ({ isOpen, onClose, application, onUpdate }) => {
  const { role } = useAuthStore()
  const [isReanalyzing, setIsReanalyzing] = useState(false)
  const [isHiring, setIsHiring] = useState(false)
  const [showHireModal, setShowHireModal] = useState(false)
  const [credibility, setCredibility] = useState(null)
  const [loadingCredibility, setLoadingCredibility] = useState(false)
  const [showCredibility, setShowCredibility] = useState(false)

  // Onboarding Templates State
  const [templates, setTemplates] = useState([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')

  // Hire Form States
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [salary, setSalary] = useState('')
  const [joiningDate, setJoiningDate] = useState('')
  const [employeeCode, setEmployeeCode] = useState('')

  // Prefill hire form when job changes
  useEffect(() => {
    if (application) {
      setDesignation(application.job_title || '')
      setDepartment(application.department || '')
      setJoiningDate(new Date().toISOString().split('T')[0])
      setSalary('800000') // default mock salary
    }
  }, [application])

  // Fetch onboarding templates when hire modal opens
  useEffect(() => {
    if (showHireModal) {
      listOnboardingTemplates()
        .then(data => {
          setTemplates(data || [])
          setSelectedTemplateId('')
        })
        .catch(err => {
          console.error('Failed to load onboarding templates', err)
        })
    }
  }, [showHireModal])

  // Handle Escape key close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!application) return null

  const analysis = application.ai_analysis || {}
  const score = analysis.fit_score || 0
  const recommendation = analysis.recommendation || 'Consider'
  const summary = analysis.summary || 'AI analysis pending or incomplete.'
  const strengths = analysis.strengths || []
  const weaknesses = analysis.weaknesses || []
  const missingSkills = analysis.missing_skills || []
  const observations = analysis.observations || []

  // Combine interview prep questions
  const interviewPrep = analysis.interview_prep || {}
  const allQuestions = [
    ...(interviewPrep.technical_questions || []),
    ...(interviewPrep.behavioral_questions || []),
    ...(interviewPrep.probing_areas || []).map(area => `Probe Candidate's experience in: ${area}`)
  ].slice(0, 5)

  const handleLoadCredibility = async (force = false) => {
    if (!application?.id) return
    setLoadingCredibility(true)
    try {
      const data = await getApplicationCredibility(application.id, force)
      setCredibility(data)
      setShowCredibility(true)
    } catch (err) {
      console.error('Failed to load credibility:', err)
      toast.error('Could not load credibility report')
    } finally {
      setLoadingCredibility(false)
    }
  }

  const handleReanalyze = async () => {
    setIsReanalyzing(true)
    try {
      let updatedApp;
      if (application.id >= 200 && application.id <= 210) {
        // Mock application! Bypass backend call and resolve locally.
        await new Promise(resolve => setTimeout(resolve, 1000))
        updatedApp = {
          ...application,
          ai_analysis: {
            ...application.ai_analysis,
            fit_score: Math.min(100, (application.ai_analysis?.fit_score || 70) + 5),
            observations: [...(application.ai_analysis?.observations || []), 'Re-analysis verified skill enhancements.']
          }
        }
      } else {
        const data = await reanalyzeApplication(application.id)
        updatedApp = data.application
      }
      toast.success('AI analysis updated successfully!')
      if (onUpdate) onUpdate(updatedApp)
    } catch (err) {
      console.error(err)
      toast.error('Re-run analysis failed. Using cached data.')
    } finally {
      setIsReanalyzing(false)
    }
  }

  const handleHireSubmit = async (e) => {
    e.preventDefault()
    setIsHiring(true)
    try {
      const parsedSalary = salary ? parseFloat(salary) : null
      const hirePayload = {
        department,
        designation,
        salary: parsedSalary,
        joining_date: joiningDate,
        employee_code: employeeCode || null,
        onboarding_template_id: selectedTemplateId ? parseInt(selectedTemplateId) : null
      }
      
      let updatedApp;
      if (application.id >= 200 && application.id <= 210) {
        // Mock application! Bypass backend call and resolve locally.
        await new Promise(resolve => setTimeout(resolve, 800))
        updatedApp = {
          ...application,
          status: 'Hired',
          employee_code: employeeCode || 'EMP-MOCK-' + application.id,
          joining_date: joiningDate,
          department: department,
          designation: designation,
          salary: parsedSalary
        }
      } else {
        const data = await hireCandidate(application.id, hirePayload)
        updatedApp = data.application
      }
      
      toast.success(`${application.candidate_username} has been successfully hired!`)
      setShowHireModal(false)
      if (onUpdate) onUpdate(updatedApp)
      onClose()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to complete hire operation.')
    } finally {
      setIsHiring(false)
    }
  }

  // Map recommendation badges
  const getRecBadge = (rec) => {
    const norm = rec.toLowerCase()
    if (norm.includes('strong')) {
      return { label: 'STRONG HIRE', style: 'bg-success-bg text-success-primary border-success-primary/30' }
    }
    if (norm.includes('recom')) {
      return { label: 'RECOMMENDED HIRE', style: 'bg-success-bg text-success-primary border-success-primary/20' }
    }
    if (norm.includes('reject') || norm.includes('pass')) {
      return { label: 'PASS / REJECT', style: 'bg-danger-bg text-danger-primary border-danger-primary/30' }
    }
    return { label: 'MAYBE / CONSIDER', style: 'bg-warning-bg text-warning-custom border-warning-custom/30' }
  }

  const badge = getRecBadge(recommendation)

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop Blur */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 bg-black z-40"
            />

            {/* Slide-over Drawer (560px wide) */}
            <motion.div
              initial={{ x: 560 }}
              animate={{ x: 0 }}
              exit={{ x: 560 }}
              transition={{ type: 'tween', duration: 0.3, ease: 'easeOut' }}
              className="fixed right-0 top-0 bottom-0 w-full max-w-[560px] h-screen bg-bg-surface border-l border-border-custom shadow-2xl flex flex-col z-50 overflow-hidden text-txt-primary select-none"
            >
              {/* Header */}
              <div className="p-6 border-b border-border-custom flex items-center justify-between bg-bg-page/50">
                <div className="space-y-1">
                  <h3 className="text-lg font-semibold tracking-tight">{application.candidate_username}</h3>
                  <div className="flex items-center space-x-2 text-xs text-txt-secondary">
                    <Briefcase size={13} className="text-brand-indigo" />
                    <span>{application.job_title}</span>
                    <span className="text-txt-tertiary">•</span>
                    <Calendar size={13} />
                    <span>{new Date(application.application_date).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <StatusPill status={application.status} />
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated hover:text-txt-primary text-txt-secondary transition-colors cursor-pointer"
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
                
                {/* AI Score Donut Section */}
                <div className="bg-bg-page/40 rounded-xl border border-border-custom p-4 flex flex-col items-center justify-center text-center">
                  <div className="flex flex-row space-x-12 items-center justify-center">
                    <div className="flex flex-col items-center">
                      <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider mb-2">Resume Match</span>
                      <AIScoreDonut score={score} />
                    </div>
                    {application.interview_analysis && application.interview_analysis.job_fit_report && (
                      <div className="flex flex-col items-center">
                        <span className="text-[10px] font-bold text-brand-indigo uppercase tracking-wider mb-2">Interview Score</span>
                        <AIScoreDonut score={application.interview_analysis.job_fit_report?.jobFit || (application.interview_analysis.avg_score ? application.interview_analysis.avg_score * 10 : 0)} />
                      </div>
                    )}
                  </div>
                  
                  {/* Recommendation Badge */}
                  <div className={`mt-4 inline-flex items-center justify-center rounded-full border px-4 py-1 text-xs font-bold uppercase tracking-wider ${badge.style}`}>
                    {badge.label}
                  </div>
                  
                  {/* Summary Text */}
                  <p className="mt-4 text-xs text-txt-secondary italic max-w-md leading-relaxed">
                    "{summary}"
                  </p>
                  
                  {/* Interview Summary if available */}
                  {application.interview_analysis && application.interview_analysis.job_fit_report && application.interview_analysis.job_fit_report.strengths && (
                    <div className="mt-4 p-3 bg-brand-indigo/5 border border-brand-indigo/10 rounded-lg w-full text-left">
                       <span className="text-[10px] font-bold text-brand-indigo uppercase tracking-wider block mb-1">Interview Intelligence</span>
                       <p className="text-xs text-txt-primary">
                         Identified Strengths: {application.interview_analysis.job_fit_report.strengths.join(", ")}
                       </p>
                       <p className="text-xs text-txt-primary mt-1">
                         Identified Weaknesses: {application.interview_analysis.job_fit_report.weaknesses?.join(", ")}
                       </p>
                    </div>
                  )}
                </div>

                {/* Strengths Grid */}
                {strengths.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Strengths</span>
                    <div className="flex flex-wrap gap-2">
                      {strengths.map((str, idx) => (
                        <span key={idx} className="inline-flex items-center space-x-1 bg-success-bg/30 text-success-primary border border-success-primary/20 px-2.5 py-1 rounded-lg text-xs">
                          <Check size={12} className="flex-shrink-0" />
                          <span>{str}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Weaknesses Grid */}
                {weaknesses.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Weaknesses</span>
                    <div className="flex flex-wrap gap-2">
                      {weaknesses.map((weak, idx) => (
                        <span key={idx} className="inline-flex items-center space-x-1 bg-danger-bg/30 text-danger-primary border border-danger-primary/20 px-2.5 py-1 rounded-lg text-xs">
                          <span className="text-[10px] font-bold leading-none">✕</span>
                          <span>{weak}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Missing Skills Grid */}
                {missingSkills.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Missing Skills</span>
                    <div className="flex flex-wrap gap-2">
                      {missingSkills.map((skill, idx) => (
                        <span key={idx} className="inline-flex items-center space-x-1 bg-warning-bg/30 text-warning-custom border border-warning-custom/20 px-2.5 py-1 rounded-lg text-xs">
                          <AlertTriangle size={12} className="flex-shrink-0" />
                          <span>{skill}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Observations */}
                {observations.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Key Observations</span>
                    <ul className="list-disc pl-4 space-y-1.5 text-xs text-txt-secondary leading-relaxed">
                      {observations.map((obs, idx) => (
                        <li key={idx}>{obs}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Interview Prep Questions */}
                {allQuestions.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Suggested Interview Questions</span>
                    <div className="bg-bg-page border border-border-custom rounded-xl p-4 space-y-3">
                      {allQuestions.map((q, idx) => (
                        <div key={idx} className="flex items-start space-x-2.5 text-xs text-txt-secondary">
                          <span className="text-brand-indigo font-bold">{idx + 1}.</span>
                          <span className="leading-relaxed">{q}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Credibility Analysis Section */}
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider flex items-center gap-1.5">
                    <Shield size={12} /> Candidate Credibility
                  </span>
                  {!showCredibility ? (
                    <button
                      onClick={() => handleLoadCredibility()}
                      disabled={loadingCredibility}
                      className="w-full border border-dashed border-border-custom rounded-xl p-4 text-center hover:bg-bg-page transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {loadingCredibility ? (
                        <div className="flex items-center justify-center gap-2 text-txt-secondary">
                          <RefreshCw size={14} className="animate-spin" />
                          <span className="text-xs">Analyzing resume claims against interview evidence...</span>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          <Shield size={20} className="mx-auto text-txt-tertiary" />
                          <p className="text-xs text-txt-secondary">Compare resume claims with interview responses</p>
                          <p className="text-[10px] text-txt-tertiary">Evidence-based skill verification</p>
                        </div>
                      )}
                    </button>
                  ) : (
                    <div className="bg-bg-page border border-border-custom rounded-xl p-4 space-y-3">
                      {credibility?.credibility_score !== null ? (
                        <>
                          <div className="flex items-center gap-4">
                            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
                              credibility.credibility_score >= 75 ? 'bg-green-100' :
                              credibility.credibility_score >= 60 ? 'bg-yellow-100' :
                              credibility.credibility_score >= 40 ? 'bg-orange-100' : 'bg-red-100'
                            }`}>
                              <span className={`text-2xl font-bold ${
                                credibility.credibility_score >= 75 ? 'text-green-600' :
                                credibility.credibility_score >= 60 ? 'text-yellow-600' :
                                credibility.credibility_score >= 40 ? 'text-orange-600' : 'text-red-600'
                              }`}>{credibility.credibility_score}</span>
                            </div>
                            <div>
                              <p className="text-sm font-semibold text-txt-primary">{credibility.recommendation}</p>
                              <p className="text-[10px] text-txt-tertiary">
                                Resume: {credibility.resume_score ?? '—'} | Interview: {credibility.interview_avg_score !== null ? `${credibility.interview_avg_score.toFixed(1)}/10` : 'N/A'}
                              </p>
                            </div>
                            <button
                              onClick={() => handleLoadCredibility(true)}
                              className="ml-auto text-txt-tertiary hover:text-txt-secondary"
                              title="Re-analyze"
                            >
                              <RefreshCw size={14} />
                            </button>
                          </div>

                          {credibility.supported_claims?.length > 0 && (
                            <div>
                              <p className="text-[10px] font-semibold text-green-600 uppercase mb-1.5 flex items-center gap-1">
                                <Check size={11} /> Supported ({credibility.supported_claims.length})
                              </p>
                              <div className="space-y-1">
                                {credibility.supported_claims.map((item, i) => (
                                  <div key={i} className="flex items-start gap-1.5 text-[11px] p-1.5 bg-green-50 rounded">
                                    <Check size={11} className="text-green-500 mt-0.5 shrink-0" />
                                    <div>
                                      <span className="font-medium text-gray-700">{item.claim}</span>
                                      <p className="text-gray-400">{item.explanation}</p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {credibility.weak_claims?.length > 0 && (
                            <div>
                              <p className="text-[10px] font-semibold text-yellow-600 uppercase mb-1.5 flex items-center gap-1">
                                <AlertTriangle size={11} /> Weak ({credibility.weak_claims.length})
                              </p>
                              <div className="space-y-1">
                                {credibility.weak_claims.map((item, i) => (
                                  <div key={i} className="flex items-start gap-1.5 text-[11px] p-1.5 bg-yellow-50 rounded">
                                    <AlertTriangle size={11} className="text-yellow-500 mt-0.5 shrink-0" />
                                    <div>
                                      <span className="font-medium text-gray-700">{item.claim}</span>
                                      <p className="text-gray-400">{item.explanation}</p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {credibility.missing_evidence?.length > 0 && (
                            <div>
                              <p className="text-[10px] font-semibold text-red-500 uppercase mb-1.5 flex items-center gap-1">
                                <X size={11} /> Missing Evidence ({credibility.missing_evidence.length})
                              </p>
                              <div className="space-y-1">
                                {credibility.missing_evidence.map((item, i) => (
                                  <div key={i} className="flex items-start gap-1.5 text-[11px] p-1.5 bg-red-50 rounded">
                                    <X size={11} className="text-red-400 mt-0.5 shrink-0" />
                                    <div>
                                      <span className="font-medium text-gray-700">{item.claim}</span>
                                      <p className="text-gray-400">{item.explanation}</p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {credibility.followup_topics?.length > 0 && (
                            <div>
                              <p className="text-[10px] font-semibold text-blue-600 uppercase mb-1.5 flex items-center gap-1">
                                <HelpCircle size={11} /> Follow-Up Topics
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {credibility.followup_topics.map((topic, i) => (
                                  <span key={i} className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">
                                    {topic}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          <p className="text-[9px] text-txt-tertiary flex items-center gap-1 pt-1 border-t border-border-custom">
                            <Shield size={10} /> Evidence-based skill verification. Not a lie detector.
                          </p>
                        </>
                      ) : (
                        <div className="text-center py-3">
                          <p className="text-xs text-txt-secondary">
                            {credibility?.status === 'no_interview_data'
                              ? 'No interview sessions found for this candidate.'
                              : 'Credibility data unavailable.'}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>

              </div>

              {/* Bottom Sticky Action Panel */}
              <div className="p-4 border-t border-border-custom bg-bg-surface flex items-center space-x-3">
                <button
                  onClick={handleReanalyze}
                  disabled={isReanalyzing || isHiring}
                  className={`flex-1 h-9 rounded-lg border border-ai-teal text-ai-teal hover:bg-ai-teal/10 font-semibold text-xs transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50 ${
                    isReanalyzing ? 'animate-pulse' : ''
                  }`}
                >
                  <RefreshCw size={13} className={isReanalyzing ? 'animate-spin' : ''} />
                  <span>{isReanalyzing ? 'Analyzing candidate...' : 'Re-run AI Analysis'}</span>
                </button>

                {(role === 'hr' || role === 'admin') && application.status !== 'Hired' && (
                  <button
                    onClick={() => setShowHireModal(true)}
                    disabled={isReanalyzing || isHiring}
                    className="flex-1 h-9 bg-success-primary hover:bg-success-primary/90 text-white font-semibold text-xs rounded-lg flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                  >
                    <Award size={13} />
                    <span>Hire Candidate</span>
                  </button>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Hire & Convert to Employee Modal */}
      {showHireModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowHireModal(false)} />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-md bg-bg-elevated border border-border-hover-custom rounded-2xl p-6 relative z-10 shadow-2xl space-y-4 text-txt-primary"
          >
            <div>
              <h3 className="text-base font-semibold">Convert to Employee Profile</h3>
              <p className="text-xs text-txt-secondary mt-1">
                Establish a new personnel file for <span className="font-bold text-txt-primary">{application.candidate_username}</span> in the HRMS databases.
              </p>
            </div>

            <form onSubmit={handleHireSubmit} className="space-y-3.5">
              
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-txt-secondary uppercase">Department</label>
                  <input
                    type="text"
                    required
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-txt-secondary uppercase">Designation</label>
                  <input
                    type="text"
                    required
                    value={designation}
                    onChange={(e) => setDesignation(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-txt-secondary uppercase">Salary (Annual INR)</label>
                  <input
                    type="number"
                    required
                    value={salary}
                    onChange={(e) => setSalary(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-txt-secondary uppercase">Employee Code</label>
                  <input
                    type="text"
                    placeholder="TF-00001 (Auto if empty)"
                    value={employeeCode}
                    onChange={(e) => setEmployeeCode(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-txt-secondary uppercase block">Joining Date</label>
                  <input
                    type="date"
                    required
                    value={joiningDate}
                    onChange={(e) => setJoiningDate(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-txt-secondary uppercase block">Onboarding Plan</label>
                  <select
                    value={selectedTemplateId}
                    onChange={(e) => setSelectedTemplateId(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                  >
                    <option value="">Auto-Assign (Dept Match)</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-4 flex items-center space-x-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowHireModal(false)}
                  className="px-4 py-1.5 border border-border-custom text-txt-secondary hover:text-txt-primary text-xs font-semibold rounded-lg hover:bg-bg-page transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isHiring}
                  className="px-4 py-1.5 bg-success-primary text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-1 cursor-pointer hover:bg-success-primary/95 disabled:opacity-50"
                >
                  {isHiring ? 'Processing...' : 'Confirm Hire'}
                </button>
              </div>

            </form>
          </motion.div>
        </div>
      )}
    </>
  )
}
export default AnalysisDrawer
