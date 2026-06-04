import React from 'react'
import { UserCheck, FileText, GitMerge, Award, AlertCircle, AlertTriangle, UserX, Clock, UserCheck2, FileSignature } from 'lucide-react'

export const HRReviewQueue = ({ reviewQueue = {}, navigate }) => {
  const pendingProfiles = reviewQueue.pending_profiles || []
  const pendingDocs = reviewQueue.pending_documents || []
  const pendingOnboarding = reviewQueue.pending_onboarding_assignments || []
  const overdueTrainings = reviewQueue.overdue_trainings || []
  const incompleteCandidates = reviewQueue.incomplete_candidates || []
  const incompleteEmployees = reviewQueue.incomplete_employees || []

  const queues = [
    {
      title: "Pending Profile Reviews",
      icon: <UserCheck2 size={16} />,
      iconBg: "bg-brand-indigo/10 text-brand-indigo",
      count: pendingProfiles.length,
      description: "Profiles completed by users and awaiting HR verification.",
      items: pendingProfiles.slice(0, 3).map(item => ({
        label: item.name,
        badge: `${item.completion_percent}%`,
        type: item.type
      })),
      actionLabel: "Review Profiles",
      action: () => {
        const first = pendingProfiles[0];
        if (first?.type === 'Candidate') {
          navigate('/hr/candidates');
        } else {
          navigate('/hr/directory');
        }
      }
    },
    {
      title: "Pending Document Verification",
      icon: <FileText size={16} />,
      iconBg: "bg-teal-500/10 text-teal-500",
      count: pendingDocs.length,
      description: "Uploaded credentials requiring verification checks.",
      items: pendingDocs.slice(0, 3).map(item => ({
        label: `@${item.username}`,
        badge: item.document_type
      })),
      actionLabel: "Verify Documents",
      action: () => navigate('/hr/documents')
    },
    {
      title: "Missing Onboarding Assignments",
      icon: <GitMerge size={16} />,
      iconBg: "bg-orange-500/10 text-orange-500",
      count: pendingOnboarding.length,
      description: "Hired employees who do not have an onboarding template assigned.",
      items: pendingOnboarding.slice(0, 3).map(item => ({
        label: item.name,
        badge: item.employee_code || "Hired"
      })),
      actionLabel: "Assign Onboarding",
      action: () => navigate('/hr/onboarding')
    },
    {
      title: "Incomplete Employee Profiles",
      icon: <AlertCircle size={16} />,
      iconBg: "bg-amber-500/10 text-amber-500",
      count: incompleteEmployees.length,
      description: "Hired employees with profiles currently under 100% completion.",
      items: incompleteEmployees.slice(0, 3).map(item => ({
        label: item.name,
        badge: `${item.completion_percent}%`
      })),
      actionLabel: "View Employees",
      action: () => navigate('/hr/directory')
    },
    {
      title: "Incomplete Candidate Profiles",
      icon: <UserX size={16} />,
      iconBg: "bg-slate-500/10 text-slate-500",
      count: incompleteCandidates.length,
      description: "Registered candidates who haven't completed their setup steps.",
      items: incompleteCandidates.slice(0, 3).map(item => ({
        label: item.name,
        badge: `${item.completion_percent}%`
      })),
      actionLabel: "View Candidates",
      action: () => navigate('/hr/candidates')
    },
    {
      title: "Overdue Training Assignments",
      icon: <Award size={16} />,
      iconBg: "bg-red-500/10 text-red-500",
      count: overdueTrainings.length,
      description: "Assigned courses past their scheduled completion due dates.",
      items: overdueTrainings.slice(0, 3).map(item => ({
        label: item.name,
        badge: item.program_title
      })),
      actionLabel: "Track Training",
      action: () => navigate('/hr/training')
    }
  ]

  return (
    <div className="space-y-4">
      <h3 className="text-[10px] font-bold tracking-wider uppercase text-txt-secondary flex items-center gap-1.5">
        <FileSignature size={12} className="text-brand-indigo" />
        HR Operational Review Queues
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {queues.map((q, idx) => (
          <div key={idx} className="bg-bg-surface border border-border-custom hover:border-border-hover-custom p-5 rounded-xl flex flex-col justify-between space-y-4 shadow-xs transition-all relative group overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-brand-indigo/3 rounded-full blur-xl -mr-6 -mt-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider">{q.title}</span>
                <div className={`p-1.5 rounded-lg ${q.iconBg}`}>
                  {q.icon}
                </div>
              </div>
              <div className="text-2xl font-black text-txt-primary flex items-baseline gap-1.5">
                {q.count}
                {q.count > 0 && <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />}
              </div>
              <p className="text-[10px] text-txt-secondary leading-normal">
                {q.description}
              </p>
              
              {q.count > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-border-custom/30 mt-2">
                  {q.items.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center text-[10px] text-txt-secondary bg-bg-page/40 p-1.5 rounded border border-border-custom/20 hover:border-border-custom/50 transition-colors">
                      <span className="truncate max-w-[120px] font-medium">{item.label}</span>
                      <span className="text-[8px] bg-bg-surface border border-border-custom/40 px-1.5 py-0.5 rounded text-txt-tertiary uppercase font-bold truncate max-w-[90px]">{item.badge}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={q.action}
              disabled={q.count === 0}
              className="w-full py-2 bg-brand-indigo/10 hover:bg-brand-indigo/20 text-brand-indigo disabled:bg-bg-page/50 disabled:text-txt-tertiary text-[10px] font-bold rounded-lg cursor-pointer transition-colors shadow-xs disabled:opacity-50 disabled:cursor-not-allowed text-center"
            >
              {q.actionLabel}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default HRReviewQueue
