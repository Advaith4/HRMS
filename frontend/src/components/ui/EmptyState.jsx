import React from 'react'
import {
  Inbox, Briefcase, FileText, Clock, CheckCircle, Search, UserCheck,
  Award, GitMerge, Users, Calendar, HelpCircle
} from 'lucide-react'

// Only the icons actually used across the app — no wildcard import
const ICON_MAP = {
  Inbox, Briefcase, FileText, Clock, CheckCircle, Search, UserCheck,
  Award, GitMerge, Users, Calendar, HelpCircle,
}

export const EmptyState = ({ iconName = 'Inbox', title = 'No data available', description = 'Try adjusting your search filters or check back later.', actionLabel, onAction }) => {
  const Icon = ICON_MAP[iconName] || Inbox

  return (
    <div className="flex flex-col items-center justify-center text-center p-12 border border-dashed border-border-custom rounded-xl bg-bg-surface/30">
      <div className="p-4 rounded-full bg-bg-page border border-border-custom text-txt-tertiary mb-4">
        <Icon size={36} />
      </div>
      <h3 className="text-base font-semibold text-txt-primary">{title}</h3>
      <p className="mt-1 text-sm text-txt-secondary max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-6 inline-flex items-center justify-center rounded-lg bg-brand-indigo px-4 py-2 text-xs font-semibold text-white hover:bg-brand-indigo-hover active:scale-98 transition-all"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
export default EmptyState
