import React from 'react'
import { AlertTriangle, Clock, ArrowRight, ClipboardCheck, Sparkles } from 'lucide-react'

export const PendingActionsWidget = ({ reviewQueue = {}, leaves = [], onActionClick }) => {
  const pendingDocs = reviewQueue.pending_documents || []
  const pendingOnboarding = reviewQueue.pending_onboarding_assignments || []
  const overdueTrainings = reviewQueue.overdue_trainings || []
  const pendingLeaves = leaves.filter(l => l.status === 'Pending')

  const actions = []

  if (pendingLeaves.length > 0) {
    actions.push({
      id: 'leaves',
      title: 'Awaiting Leave Decisions',
      detail: `${pendingLeaves.length} employee time-off request(s) require HR/Manager approval.`,
      urgency: 'high',
      iconColor: 'text-amber-500',
      actionLabel: 'Go to Leaves'
    })
  }

  if (pendingDocs.length > 0) {
    actions.push({
      id: 'documents',
      title: 'Verify Submitted Credentials',
      detail: `${pendingDocs.length} compliance document(s) uploaded by staff are ready for auditing.`,
      urgency: 'medium',
      iconColor: 'text-teal-500',
      actionLabel: 'Verify Files'
    })
  }

  if (pendingOnboarding.length > 0) {
    actions.push({
      id: 'onboarding',
      title: 'Unassigned Onboarding Journeys',
      detail: `${pendingOnboarding.length} hired employee(s) are missing procedural template assignments.`,
      urgency: 'high',
      iconColor: 'text-orange-500',
      actionLabel: 'Assign Templates'
    })
  }

  if (overdueTrainings.length > 0) {
    actions.push({
      id: 'training',
      title: 'Overdue Course Assignments',
      detail: `${overdueTrainings.length} active training assignments have passed their scheduled due date.`,
      urgency: 'low',
      iconColor: 'text-red-500',
      actionLabel: 'Audit Training'
    })
  }

  return (
    <div className="rounded-xl border border-border-custom bg-bg-surface p-5 shadow-xs space-y-4">
      <div className="flex items-center justify-between border-b border-border-custom/50 pb-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-txt-primary flex items-center gap-1.5">
          <AlertTriangle size={14} className="text-warning-primary animate-pulse" />
          Urgent Action Center
        </h4>
        <span className="text-[9px] bg-warning-bg/20 text-warning-primary border border-warning-primary/20 px-2 py-0.5 rounded-full font-bold uppercase">
          {actions.length} Alerts
        </span>
      </div>

      {actions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-center text-xs text-txt-tertiary">
          <div className="p-2 rounded-full bg-success-bg/10 text-success-primary mb-2">
            <ClipboardCheck size={20} />
          </div>
          <p className="font-bold text-txt-secondary flex items-center gap-1">
            <Sparkles size={12} className="text-yellow-400" />
            All clear!
          </p>
          <p className="text-[10px] opacity-80 mt-0.5">No immediate items require administrative attention.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {actions.map((act, idx) => (
            <div key={idx} className="flex items-start justify-between p-3.5 bg-bg-page/40 border border-border-custom rounded-xl hover:border-border-hover-custom transition-all gap-4 text-xs">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${act.urgency === 'high' ? 'bg-red-500' : act.urgency === 'medium' ? 'bg-amber-500' : 'bg-blue-400'}`} />
                  <span className="font-bold text-txt-primary">{act.title}</span>
                </div>
                <p className="text-[10px] text-txt-secondary leading-relaxed">{act.detail}</p>
              </div>
              <button
                onClick={() => onActionClick(act.id)}
                className="shrink-0 text-[10px] font-bold text-brand-indigo hover:underline inline-flex items-center gap-1 cursor-pointer transition-all hover:translate-x-0.5"
              >
                {act.actionLabel}
                <ArrowRight size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default PendingActionsWidget
