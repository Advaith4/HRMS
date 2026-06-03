import React from 'react'

const statusStyles = {
  pending: 'bg-warning-bg text-warning-primary border border-warning-primary/20',
  active: 'bg-success-bg text-success-primary border border-success-primary/20',
  closed: 'bg-bg-surface text-txt-secondary border border-border-custom',
  hired: 'bg-success-bg text-success-primary border border-success-primary/20',
  rejected: 'bg-danger-bg text-danger-primary border border-danger-primary/20',
  'under review': 'bg-info-bg text-info-primary border border-info-primary/20',
  under_review: 'bg-info-bg text-info-primary border border-info-primary/20',
  applied: 'bg-warning-bg text-warning-primary border border-warning-primary/20',
  approved: 'bg-success-bg text-success-primary border border-success-primary/20',
  screening: 'bg-brand-indigo-muted text-brand-indigo border border-brand-indigo/30',
  interview: 'bg-violet-100 text-violet-700 border border-violet-200',
  offer: 'bg-warning-bg text-warning-primary border border-warning-primary/30',
}

export const StatusPill = ({ status }) => {
  const normalized = (status || '').toLowerCase().trim()
  const styleClass = statusStyles[normalized] || 'bg-bg-surface text-txt-secondary border border-border-custom'
  
  // Format readable status
  let label = status || 'Unknown'
  if (normalized === 'under_review') label = 'Under Review'
  
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${styleClass}`}>
      {label}
    </span>
  )
}
export default StatusPill
