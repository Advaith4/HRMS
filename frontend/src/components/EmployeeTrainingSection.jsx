import React from 'react'
import { StatusPill } from './ui/StatusPill'
import { EmptyState } from './ui/EmptyState'

export const EmployeeTrainingSection = ({
  trainingAssignments,
  loadingTraining,
  handleTrainingProgress,
  onAskAssistant,
}) => {
  const [filter, setFilter] = React.useState('All')

  const total = trainingAssignments?.length || 0
  const completed = trainingAssignments?.filter(t => t.status === 'Completed').length || 0
  const pending = total - completed

  const filteredAssignments = (trainingAssignments || []).filter((assignment) => {
    if (filter === 'Completed') return assignment.status === 'Completed'
    if (filter === 'Pending') return assignment.status !== 'Completed'
    return true
  })

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border-custom bg-bg-surface p-6">
        <div className="border-b border-border-custom pb-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-semibold text-txt-primary">My Training & Learning</h4>
            <p className="text-[11px] text-txt-secondary font-medium mt-0.5">Track your training programs and explore custom upskilling paths</p>
          </div>
        </div>

        {/* Training tab metrics overview */}
        {total > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-bg-page/50 border border-border-custom p-3 rounded-lg text-center">
              <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Total Assigned</span>
              <span className="text-base font-extrabold text-txt-primary block mt-1">{total}</span>
            </div>
            <div className="bg-bg-page/50 border border-border-custom p-3 rounded-lg text-center">
              <span className="text-[10px] font-bold text-success-primary uppercase tracking-wider block">Completed</span>
              <span className="text-base font-extrabold text-success-primary block mt-1">{completed}</span>
            </div>
            <div className="bg-bg-page/50 border border-border-custom p-3 rounded-lg text-center">
              <span className="text-[10px] font-bold text-warning-primary uppercase tracking-wider block">Pending</span>
              <span className="text-base font-extrabold text-warning-primary block mt-1">{pending}</span>
            </div>
          </div>
        )}

        {/* Filter selectors */}
        {total > 0 && (
          <div className="flex space-x-2 mb-6">
            {['All', 'Pending', 'Completed'].map((opt) => (
              <button
                key={opt}
                onClick={() => setFilter(opt)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                  filter === opt
                    ? 'bg-brand-indigo border-brand-indigo text-white shadow-sm'
                    : 'bg-bg-page border-border-custom text-txt-secondary hover:text-txt-primary'
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        {loadingTraining ? (
          <div className="text-xs text-txt-tertiary py-8 text-center">Loading training assignments...</div>
        ) : total === 0 ? (
          <div className="space-y-8">
            <div className="p-6 text-center border border-dashed border-border-custom rounded-xl bg-bg-page/35 space-y-2">
              <h5 className="text-xs font-bold text-txt-primary">No training assigned yet</h5>
              <p className="text-[10px] text-txt-secondary max-w-sm mx-auto leading-relaxed">
                Your manager hasn't assigned specific courses. In the meantime, you can explore standard learning paths recommended from our Company Knowledge Base.
              </p>
            </div>
            
            <div className="space-y-4">
              <h5 className="text-[10px] font-bold uppercase tracking-wider text-txt-secondary">Recommended Company Learning Paths</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  {
                    title: "Backend Engineering",
                    desc: "Master backend services, FastAPI APIs, PostgreSQL database optimization, and automated testing.",
                    skills: "Python, FastAPI, SQLModel, PostgreSQL, Pytest",
                    prompt: "Explain the Backend Engineering learning path"
                  },
                  {
                    title: "System Design",
                    desc: "Learn microservices architecture, caching strategies, distributed locking, and systems scaling.",
                    skills: "Microservices, System Architecture, Redis, Docker",
                    prompt: "Explain the System Design learning path"
                  },
                  {
                    title: "Leadership",
                    desc: "Build professional mentorship, agile management, conflict resolution, and technical guidance skills.",
                    skills: "Agile, Team Mentoring, Technical Leadership",
                    prompt: "Explain the Leadership learning path"
                  },
                  {
                    title: "Communication",
                    desc: "Enhance your technical writing, stakeholder management, presentation design, and collaboration.",
                    skills: "Professional Writing, Presentations, Collaboration",
                    prompt: "Explain the Communication learning path"
                  }
                ].map((path, idx) => (
                  <div key={idx} className="border border-border-custom rounded-xl bg-bg-page p-4 flex flex-col justify-between space-y-4 hover:border-brand-indigo/35 transition-colors">
                    <div className="space-y-2">
                      <h6 className="text-xs font-bold text-txt-primary">{path.title}</h6>
                      <p className="text-[11px] text-txt-secondary leading-relaxed">{path.desc}</p>
                      <div className="text-[9px] text-txt-secondary">
                        <span className="font-semibold text-txt-primary font-mono">Core Skills:</span> {path.skills}
                      </div>
                    </div>
                    <button
                      onClick={() => onAskAssistant && onAskAssistant(path.prompt)}
                      className="w-full py-1.5 border border-brand-indigo/40 hover:border-brand-indigo hover:bg-brand-indigo-muted/15 text-brand-indigo text-[10px] font-bold rounded-lg cursor-pointer transition-colors text-center"
                    >
                      Ask AI Assistant
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredAssignments.map((assignment) => (
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
