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

export const MetricCard = ({ iconName, label, value, delta, deltaType = 'increase', hoverColor = 'indigo' }) => {
  const Icon = ICON_MAP[iconName] || HelpCircle

  
  const isIncrease = deltaType === 'increase'
  const deltaColor = isIncrease ? 'text-success-primary bg-success-bg/40' : 'text-danger-primary bg-danger-bg/40'
  const barColor = hoverColor === 'teal' ? 'bg-ai-teal' : 'bg-brand-indigo'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.25 }}
      className="group relative overflow-hidden rounded-xl border border-border-custom bg-bg-surface p-6 cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-txt-secondary">{label}</span>
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

      {/* Subtle bottom hover bar */}
      <div className={`absolute bottom-0 left-0 right-0 h-[3px] w-full ${barColor} transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left`} />
    </motion.div>
  )
}
export default MetricCard
