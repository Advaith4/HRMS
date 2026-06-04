import React from 'react'
import { FileUp, ShieldCheck, CheckCircle2, AlertCircle, FileText, CheckSquare, Clock } from 'lucide-react'
import { StatusPill } from './ui/StatusPill'
import { EmptyState } from './ui/EmptyState'

export const EmployeeOnboardingSection = ({
  onboardingPlans,
  loadingOnboarding,
  handleOnboardingTaskStatus,
  handleUploadOnboardingDocument,
}) => {
  if (loadingOnboarding) {
    return (
      <div className="flex flex-col items-center justify-center py-12 rounded-xl border border-border-custom bg-bg-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
        <span className="text-xs text-txt-secondary mt-3">Loading your onboarding plans...</span>
      </div>
    )
  }

  if (!onboardingPlans || onboardingPlans.length === 0) {
    return (
      <div className="rounded-xl border border-border-custom bg-bg-surface p-6">
        <div className="border-b border-border-custom pb-4 mb-6">
          <h4 className="text-sm font-semibold">Employee Onboarding Journey</h4>
          <p className="text-[11px] text-txt-secondary mt-1">
            Complete required documentation, company formalities, policy acknowledgements, and role preparation activities before becoming fully operational.
          </p>
        </div>
        <EmptyState
          title="No onboarding plan assigned"
          description="Your onboarding checklist will appear here once HR assigns it."
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {onboardingPlans.map((plan) => {
        const reqDocs = plan.required_documents || []
        const tasks = plan.tasks || []
        
        // Understandable Weighting: Tasks = 50%, Documents = 50%
        const totalTasks = tasks.length
        const completedTasks = tasks.filter(t => t.status === 'Completed').length
        const taskProgress = totalTasks ? Math.round((completedTasks / totalTasks) * 100) : 100

        const totalDocs = reqDocs.length
        const approvedDocs = reqDocs.filter(d => d.status === 'Approved').length
        const docProgress = totalDocs ? Math.round((approvedDocs / totalDocs) * 100) : 100

        const overallProgress = Math.round((taskProgress + docProgress) / 2)

        return (
          <div key={plan.id} className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-8">
            {/* Header */}
            <div className="border-b border-border-custom pb-4">
              <h4 className="text-lg font-black text-txt-primary flex items-center gap-2">
                <span className="p-1.5 rounded bg-brand-indigo/10 text-brand-indigo">
                  <ShieldCheck size={18} />
                </span>
                Employee Onboarding Journey
              </h4>
              <p className="text-xs text-txt-secondary mt-1 max-w-3xl leading-relaxed">
                Complete required documentation, company formalities, policy acknowledgements, and role preparation activities before becoming fully operational.
              </p>
            </div>

            {/* Layout Order: Section 1 (Docs), Section 2 (Tasks), Section 3 (Verification), Section 4 (Progress) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Left Column: Sections 1 & 2 (8 cols) */}
              <div className="lg:col-span-8 space-y-8">
                
                {/* Section 1: Required Documents */}
                <div className="space-y-4">
                  <div className="border-b border-border-custom/50 pb-2">
                    <h5 className="text-xs font-bold uppercase tracking-wider text-brand-indigo flex items-center gap-2">
                      <FileText size={14} />
                      Section 1: Required Compliance Documents
                    </h5>
                    <p className="text-[10px] text-txt-tertiary mt-0.5">Submit official documents for verification. Approved files are marked in green.</p>
                  </div>

                  {reqDocs.length === 0 ? (
                    <div className="text-xs text-txt-tertiary bg-bg-page/40 border border-border-custom/50 rounded-xl p-4 text-center">
                      No compliance documents are required for this onboarding template.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {reqDocs.map((doc) => {
                        const isRejected = doc.status === 'Rejected'
                        const isApproved = doc.status === 'Approved'
                        const hasUploaded = doc.status !== 'Pending Submission'

                        return (
                          <div
                            key={doc.document_type}
                            className={`p-4 border rounded-xl flex flex-col justify-between gap-3 bg-bg-page/40 hover:border-border-custom/80 transition-all ${
                              isApproved 
                                ? 'border-success-primary/20 bg-success-bg/5' 
                                : isRejected 
                                ? 'border-red-500/20 bg-red-500/5' 
                                : 'border-border-custom'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <span className="text-xs font-bold text-txt-primary block">{doc.document_type}</span>
                                {hasUploaded && doc.uploaded_at && (
                                  <span className="text-[9px] text-txt-tertiary block mt-0.5">
                                    Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                              <StatusPill status={doc.status} />
                            </div>

                            {isRejected && doc.rejection_comment && (
                              <div className="text-[10px] text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20 leading-normal">
                                <strong>Rejection Comment:</strong> {doc.rejection_comment}
                              </div>
                            )}

                            {!isApproved && (
                              <label className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 border border-border-custom bg-bg-surface hover:border-brand-indigo/40 rounded-lg text-[10px] font-bold cursor-pointer text-txt-secondary hover:text-txt-primary transition-all">
                                <FileUp size={13} className="text-brand-indigo" />
                                {hasUploaded ? 'Re-upload Document' : 'Upload Document'}
                                <input
                                  type="file"
                                  className="hidden"
                                  onChange={(e) => handleUploadOnboardingDocument(doc.document_type, e.target.files?.[0])}
                                />
                              </label>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>

                {/* Section 2: Onboarding Tasks */}
                <div className="space-y-4">
                  <div className="border-b border-border-custom/50 pb-2">
                    <h5 className="text-xs font-bold uppercase tracking-wider text-brand-indigo flex items-center gap-2">
                      <CheckSquare size={14} />
                      Section 2: Onboarding Checkpoint Tasks
                    </h5>
                    <p className="text-[10px] text-txt-tertiary mt-0.5">Procedural tasks and handbook acknowledgements to complete.</p>
                  </div>

                  {tasks.length === 0 ? (
                    <div className="text-xs text-txt-tertiary bg-bg-page/40 border border-border-custom/50 rounded-xl p-4 text-center">
                      No checklist tasks are configured for this plan.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {tasks.map((task) => (
                        <div
                          key={task.id}
                          className="flex items-start justify-between p-4 border border-border-custom rounded-xl bg-bg-page/20 hover:border-border-custom/80 transition-all gap-4"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-txt-primary">{task.title}</span>
                              {task.required && (
                                <span className="text-[8px] font-bold text-red-400 bg-red-400/10 border border-red-400/20 px-1.5 py-0.5 rounded">
                                  Required
                                </span>
                              )}
                            </div>
                            <p className="text-[10px] text-txt-secondary leading-normal">{task.description || 'No description provided.'}</p>
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <StatusPill status={task.status} />
                            {task.status !== 'Completed' && (
                              <div className="flex gap-1.5">
                                {task.status === 'Pending' && (
                                  <button
                                    onClick={() => handleOnboardingTaskStatus(plan.id, task.id, 'In Progress')}
                                    className="px-2.5 py-1 border border-border-custom text-[10px] font-bold rounded-lg hover:border-brand-indigo/40 hover:text-txt-primary cursor-pointer transition-all bg-bg-surface"
                                  >
                                    Start
                                  </button>
                                )}
                                <button
                                  onClick={() => handleOnboardingTaskStatus(plan.id, task.id, 'Completed')}
                                  className="px-2.5 py-1 bg-success-primary hover:bg-success-primary/95 text-white text-[10px] rounded-lg font-bold cursor-pointer transition-all active:scale-98"
                                >
                                  Complete
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

              {/* Right Column: Sections 3 & 4 (4 cols) */}
              <div className="lg:col-span-4 space-y-6">
                
                {/* Section 3: Verification Status Timeline */}
                <div className="border border-border-custom/60 bg-bg-page/20 rounded-xl p-5 space-y-4">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-brand-indigo flex items-center gap-2 border-b border-border-custom/50 pb-2">
                    <Clock size={14} />
                    Section 3: Verification Timeline
                  </h5>
                  <div className="space-y-5 pl-2.5 border-l border-border-custom relative">
                    <div className="relative pl-6">
                      <span className={`absolute left-[-21px] top-0.5 w-2.5 h-2.5 rounded-full border ${plan.progress_percent >= 50 ? 'bg-success-primary border-success-primary' : 'bg-bg-page border-border-custom'}`} />
                      <div className="text-xs font-bold text-txt-primary">Profile Integrity Wizard</div>
                      <p className="text-[10px] text-txt-secondary mt-0.5">Pre-populated employee info verified or updated.</p>
                    </div>
                    
                    <div className="relative pl-6">
                      <span className={`absolute left-[-21px] top-0.5 w-2.5 h-2.5 rounded-full border ${approvedDocs === totalDocs && totalDocs > 0 ? 'bg-success-primary border-success-primary' : 'bg-bg-page border-border-custom'}`} />
                      <div className="text-xs font-bold text-txt-primary">Compliance Uploads</div>
                      <p className="text-[10px] text-txt-secondary mt-0.5">
                        {approvedDocs} / {totalDocs} approved documents. Complete files must be approved by HR.
                      </p>
                    </div>

                    <div className="relative pl-6">
                      <span className={`absolute left-[-21px] top-0.5 w-2.5 h-2.5 rounded-full border ${completedTasks === totalTasks && totalTasks > 0 ? 'bg-success-primary border-success-primary' : 'bg-bg-page border-border-custom'}`} />
                      <div className="text-xs font-bold text-txt-primary">Checkpoint Tasks</div>
                      <p className="text-[10px] text-txt-secondary mt-0.5">
                        {completedTasks} / {totalTasks} check-ins marked done. Handbook and orientation complete.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Section 4: Progress Overview */}
                <div className="border border-border-custom/60 bg-bg-page/20 rounded-xl p-5 space-y-4">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-brand-indigo flex items-center gap-2 border-b border-border-custom/50 pb-2">
                    <ShieldCheck size={14} />
                    Section 4: Progress Summary
                  </h5>
                  
                  <div className="space-y-4">
                    {/* Overall Progress Widget */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px] font-bold">
                        <span className="text-txt-secondary">Overall Journey Progress</span>
                        <span className="text-brand-indigo">{overallProgress}%</span>
                      </div>
                      <div className="w-full h-2.5 bg-bg-page border border-border-custom/50 rounded-full overflow-hidden">
                        <div className="h-full bg-brand-indigo rounded-full transition-all duration-500" style={{ width: `${overallProgress}%` }} />
                      </div>
                    </div>

                    {/* Separate Tasks Weight */}
                    <div className="space-y-1.5 pt-2 border-t border-border-custom/30">
                      <div className="flex justify-between text-[10px] font-bold text-txt-tertiary uppercase">
                        <span>Tasks Completion (50% Weight)</span>
                        <span className="text-green-500">{taskProgress}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-bg-page border border-border-custom/40 rounded-full overflow-hidden">
                        <div className="h-full bg-green-500 rounded-full transition-all duration-500" style={{ width: `${taskProgress}%` }} />
                      </div>
                      <span className="text-[9px] text-txt-secondary block">{completedTasks} of {totalTasks} checkpoints finished</span>
                    </div>

                    {/* Separate Documents Weight */}
                    <div className="space-y-1.5 pt-2 border-t border-border-custom/30">
                      <div className="flex justify-between text-[10px] font-bold text-txt-tertiary uppercase">
                        <span>Documents Approval (50% Weight)</span>
                        <span className="text-blue-500">{docProgress}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-bg-page border border-border-custom/40 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${docProgress}%` }} />
                      </div>
                      <span className="text-[9px] text-txt-secondary block">{approvedDocs} of {totalDocs} credentials verified</span>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          </div>
        )
      })}
    </div>
  )
}

export default EmployeeOnboardingSection
