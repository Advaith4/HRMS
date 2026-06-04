import React from 'react'
import { StatusPill } from './ui/StatusPill'
import { EmptyState } from './ui/EmptyState'

export const EmployeeTrainingSection = ({
  trainingAssignments,
  loadingTraining,
  handleTrainingProgress,
}) => {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border-custom bg-bg-surface p-6">
        <div className="border-b border-border-custom pb-4 mb-6">
          <h4 className="text-sm font-semibold text-txt-primary">My Training</h4>
          <p className="text-[11px] text-txt-secondary">Track training programs assigned by HR</p>
        </div>

        {loadingTraining ? (
          <div className="text-xs text-txt-tertiary py-8 text-center">Loading training assignments...</div>
        ) : trainingAssignments.length === 0 ? (
          <EmptyState title="No training assigned" description="Assigned programs will appear here." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {trainingAssignments.map((assignment) => (
              <div key={assignment.id} className="border border-border-custom rounded-xl bg-bg-page p-4 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h5 className="text-sm font-semibold text-txt-primary">{assignment.program_title}</h5>
                    <p className="text-[11px] text-txt-secondary mt-1">
                      {assignment.category} · {assignment.duration_hours}h · {assignment.difficulty}
                    </p>
                  </div>
                  <StatusPill status={assignment.status} />
                </div>
                <p className="text-xs text-txt-secondary leading-relaxed">{assignment.description || 'No description provided'}</p>
                <div className="text-[11px] text-txt-secondary">
                  <span className="font-semibold text-txt-primary">Skills:</span> {assignment.skills_covered || 'General'}
                </div>
                <div>
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <span className="text-txt-secondary">Progress</span>
                    <span className="font-bold text-brand-indigo">{assignment.progress_percent || 0}%</span>
                  </div>
                  <div className="h-2 bg-bg-surface rounded-full overflow-hidden border border-border-custom">
                    <div className="h-full bg-brand-indigo" style={{ width: `${assignment.progress_percent || 0}%` }} />
                  </div>
                </div>
                <div className="flex flex-wrap justify-end gap-2 pt-2 border-t border-border-custom">
                  {[25, 50, 75, 100].map((value) => (
                    <button
                      key={value}
                      onClick={() => handleTrainingProgress(assignment.id, value)}
                      disabled={(assignment.progress_percent || 0) >= value}
                      className="px-2.5 py-1 border border-border-custom text-[11px] rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:border-brand-indigo/40 hover:text-brand-indigo cursor-pointer transition-colors"
                    >
                      {value === 100 ? 'Complete' : `${value}%`}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default EmployeeTrainingSection
