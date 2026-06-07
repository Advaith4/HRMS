import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { X, Upload, CheckCircle, FileText, Briefcase, IndianRupee, MapPin } from 'lucide-react'
import { applyToJob } from '../../api/applications'
import { invalidateCache } from '../../api/axios'
import toast from 'react-hot-toast'

export const JobDetailDrawer = ({ isOpen, onClose, job, onApplySuccess }) => {
  const [file, setFile] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [appId, setAppId] = useState(null)

  // Clear state when drawer opens or changes
  useEffect(() => {
    if (isOpen) {
      setFile(null)
      setIsSuccess(false)
      setIsSubmitting(false)
      setAppId(null)
    }
  }, [isOpen, job])

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

  const onDrop = (acceptedFiles) => {
    const selectedFile = acceptedFiles[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      toast.success(`${selectedFile.name} loaded.`)
    } else {
      toast.error('Only PDF files are supported.')
    }
  }

  const applicationsClosed = (job?.status || 'OPEN') === 'CLOSED'

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: applicationsClosed,
  })

  if (!job) return null

  const handleSubmit = async () => {
    if (!file) {
      toast.error('Please upload your resume PDF first.')
      return
    }
    if (applicationsClosed) {
      toast.error('Applications for this position are closed.')
      return
    }

    setIsSubmitting(true)
    try {
      const result = await applyToJob(job.id, file)
      toast.success('Application submitted! AI analysis is running in the background.')
      toast('Your AI fit score will appear in My Applications shortly.', { icon: '🤖', duration: 4000 })
      setAppId(result.application.id)
      setIsSuccess(true)
      if (onApplySuccess) onApplySuccess(result.application)
      invalidateCache('/api/dashboard/candidate')
    } catch (err) {
      console.error(err)
      if (err.response?.status === 409) {
        toast.error('You already applied for this position.')
      } else {
        toast.error(err.response?.data?.detail || 'Submission failed. Please check your PDF and try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const skillPills = (job.required_skills || '')
    .split(/[,|;]+/)
    .map(s => s.trim())
    .filter(s => s.length > 0)

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black z-40"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: 480 }}
            animate={{ x: 0 }}
            exit={{ x: 480 }}
            transition={{ type: 'tween', duration: 0.3, ease: 'easeOut' }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-[480px] h-screen bg-bg-surface border-l border-border-custom shadow-2xl flex flex-col z-50 overflow-hidden text-txt-primary select-none"
          >
            {/* Header */}
            <div className="p-6 border-b border-border-custom flex items-center justify-between bg-bg-page/50">
              <div>
                <span className="text-[10px] font-bold text-brand-indigo uppercase tracking-wider block">Job Details</span>
                <h3 className="text-base font-semibold text-txt-primary mt-1">{job.title}</h3>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated hover:text-txt-primary text-txt-secondary transition-colors cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {isSuccess ? (
                /* Success State Card */
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex flex-col items-center justify-center text-center py-8 space-y-4"
                >
                  <CheckCircle size={48} className="text-success-primary animate-bounce" />
                  <div className="space-y-2">
                    <h4 className="text-base font-bold text-txt-primary">Application Submitted!</h4>
                    <p className="text-xs text-txt-secondary leading-relaxed max-w-xs mx-auto">
                      A <strong>Mandatory Proctored AI Interview</strong> is required to finalize your application for the <strong>{job.title}</strong> role.
                    </p>
                    <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg p-3 text-[11px] leading-relaxed text-left max-w-xs mx-auto">
                      <strong>⚠️ Proctoring Notice:</strong> Full-screen mode, active camera sharing, and screen sharing are strictly enforced. Switching tabs or exiting full-screen more than 3 times will cancel the interview and report it to HR.
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 w-full max-w-xs pt-2">
                    <a
                      href={`/interview?appId=${appId}`}
                      className="px-4 py-2.5 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-bold rounded-lg text-center cursor-pointer transition-all shadow-md"
                    >
                      Start Mandatory Interview
                    </a>
                    <button
                      onClick={onClose}
                      className="px-4 py-2 text-txt-secondary hover:text-txt-primary text-xs font-semibold rounded-lg transition-all"
                    >
                      Complete Later
                    </button>
                  </div>
                </motion.div>
              ) : (
                /* Application details & upload workflow */
                <>
                  {/* Stats Row */}
                  <div className="grid grid-cols-2 gap-4 bg-bg-page border border-border-custom rounded-xl p-4 text-xs">
                    <div className="space-y-1">
                      <span className="text-txt-tertiary font-medium block">Department</span>
                      <div className="flex items-center space-x-1.5 text-txt-primary font-semibold">
                        <Briefcase size={12} className="text-brand-indigo" />
                        <span>{job.department || 'N/A'}</span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-txt-tertiary font-medium block">Salary Package</span>
                      <div className="flex items-center space-x-1.5 text-ai-teal font-semibold">
                        <IndianRupee size={12} />
                        <span>{job.salary_range || 'Competitive'}</span>
                      </div>
                    </div>
                    <div className="space-y-1 pt-2 border-t border-border-custom/50">
                      <span className="text-txt-tertiary font-medium block">Experience Req.</span>
                      <span className="text-txt-primary font-semibold">{job.experience_required || 'Any'}</span>
                    </div>
                    <div className="space-y-1 pt-2 border-t border-border-custom/50">
                      <span className="text-txt-tertiary font-medium block">Job Location</span>
                      <div className="flex items-center space-x-1 text-txt-primary font-semibold">
                        <MapPin size={12} className="text-txt-secondary" />
                        <span>Remote / Office</span>
                      </div>
                    </div>
                  </div>

                  {/* Skills Section */}
                  {skillPills.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Required Skills</span>
                      <div className="flex flex-wrap gap-1.5">
                        {skillPills.map((skill, idx) => (
                          <span key={idx} className="bg-bg-page border border-border-custom px-2.5 py-0.5 rounded-md text-xs text-txt-secondary">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Description Box */}
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Job Description</span>
                    <p className="text-xs text-txt-secondary leading-relaxed whitespace-pre-wrap">
                      {job.description}
                    </p>
                  </div>

                  {/* Resume Dropzone Upload Area */}
                  <div className="space-y-2.5 pt-4 border-t border-border-custom">
                    <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Submit Resume (PDF Only)</span>
                    {applicationsClosed && (
                      <div className="rounded-lg border border-warning-primary/20 bg-warning-bg/30 px-3 py-2 text-xs font-medium text-warning-primary">
                        Applications for this position are closed.
                      </div>
                    )}
                    
                    <div
                      {...getRootProps()}
                      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                        applicationsClosed
                          ? 'border-border-custom bg-slate-50 cursor-not-allowed opacity-60'
                          : isDragActive
                          ? 'border-brand-indigo bg-brand-indigo-muted/30'
                          : 'border-border-custom hover:border-brand-indigo bg-bg-page/50'
                      }`}
                    >
                      <input {...getInputProps()} />
                      <div className="flex flex-col items-center justify-center space-y-2 text-txt-secondary">
                        <Upload size={24} className="text-txt-tertiary" />
                        <p className="text-xs font-semibold text-txt-primary">
                          {applicationsClosed ? 'Applications closed' : isDragActive ? 'Drop your PDF here' : 'Drag & drop your resume'}
                        </p>
                        <span className="text-[10px] text-txt-tertiary">PDF formats up to 5MB</span>
                      </div>
                    </div>

                    {/* Dropped File State */}
                    {file && (
                      <div className="flex items-center justify-between bg-bg-page border border-border-custom p-3 rounded-lg text-xs">
                        <div className="flex items-center space-x-2.5">
                          <FileText size={16} className="text-brand-indigo" />
                          <div className="truncate">
                            <span className="font-semibold text-txt-primary block truncate max-w-[200px]">
                              {file.name}
                            </span>
                            <span className="text-[10px] text-txt-tertiary">
                              {(file.size / (1024 * 1024)).toFixed(2)} MB
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => setFile(null)}
                          className="p-1 text-txt-tertiary hover:text-danger-primary transition-colors cursor-pointer"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                </>
              )}

            </div>

            {/* Footer Apply CTA */}
            {!isSuccess && (
              <div className="p-4 border-t border-border-custom bg-bg-surface">
                <button
                  onClick={handleSubmit}
                  disabled={!file || isSubmitting || applicationsClosed}
                  className="w-full h-9 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-1.5 transition-all disabled:opacity-50 active:scale-98 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Submitting Profile...</span>
                    </>
                  ) : (
                    <span>{applicationsClosed ? 'Applications Closed' : 'Submit Job Application'}</span>
                  )}
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
export default JobDetailDrawer
