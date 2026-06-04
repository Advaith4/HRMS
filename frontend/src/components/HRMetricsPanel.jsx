import React from 'react'
import { MetricCard } from './ui/MetricCard'

export const HRMetricsPanel = ({
  openJobsCount,
  totalAppsCount,
  pendingReviewCount,
  hiredCount,
  avgScore,
  loading,
}) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 rounded-xl border border-border-custom bg-bg-surface p-4 animate-pulse space-y-2">
            <div className="h-3 w-2/3 bg-border-custom rounded" />
            <div className="h-6 w-1/3 bg-border-custom rounded" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
      <MetricCard iconName="Briefcase" label="Open Job Postings" value={openJobsCount} delta="Active posts" />
      <MetricCard iconName="FileText" label="Total Applications" value={totalAppsCount} delta="In database" />
      <MetricCard iconName="Search" label="Pending Screenings" value={pendingReviewCount} delta="High priority" />
      <MetricCard iconName="UserCheck" label="Hires Completed" value={hiredCount} delta="Total headcount" hoverColor="teal" />
      <MetricCard iconName="Award" label="Avg AI Fit Score" value={`${avgScore}/100`} delta="Model scoring" hoverColor="teal" />
    </div>
  )
}

export default HRMetricsPanel
