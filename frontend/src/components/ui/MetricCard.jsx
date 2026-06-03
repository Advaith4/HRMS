import React from 'react'
import { motion } from 'framer-motion'
import {
  Briefcase, FileText, Clock, CheckCircle, Search, UserCheck,
  Award, GitMerge, HelpCircle
} from 'lucide-react'

// Only icons used via iconName prop across all MetricCard usages
const ICON_MAP = {
  Briefcase, FileText, Clock, CheckCircle, Search, UserCheck,
  Award, GitMerge, HelpCircle,
}

export const MetricCard = ({ iconName, icon: PassedIcon, label, title, value, delta, description, deltaType = 'increase', hoverColor = 'indigo' }) => {
  const displayLabel = label || title
  const Icon = PassedIcon || ICON_MAP[iconName] || HelpCircle
  
  const isIncrease = deltaType === 'increase'
  const deltaColor = isIncrease ? 'text-green-700 bg-green-50 border border-green-200' : 'text-red-700 bg-red-50 border border-red-200'
  const barColor = 'bg-brand-indigo'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.25 }}
      className="group relative overflow-hidden rounded-xl border border-border-custom bg-bg-surface p-6 cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-txt-secondary">{displayLabel}</span>
        <div className={`p-2 rounded-lg bg-bg-page border border-border-custom text-txt-secondary group-hover:text-txt-primary transition-colors`}>
          <Icon size={18} className={hoverColor === 'teal' ? 'text-ai-teal' : 'text-brand-indigo'} />
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <span className="text-3xl font-bold tracking-tight text-txt-primary">
          {value}
        </span>
        {delta && (
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${deltaColor}`}>
            {isIncrease ? '↑' : '↓'} {delta}
          </span>
        )}
      </div>

      {description && (
        <p className="mt-1.5 text-xs text-txt-tertiary font-normal">
          {description}
        </p>
      )}

      {/* Subtle bottom hover bar */}
      <div className={`absolute bottom-0 left-0 right-0 h-[3px] w-full ${barColor} transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left`} />
    </motion.div>
  )
}
export default MetricCard
