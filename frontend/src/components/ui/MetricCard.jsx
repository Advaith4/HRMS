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
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.2 }}
      className="group relative overflow-hidden rounded-xl border border-border-custom bg-bg-surface p-6 shadow-xs hover:shadow-md transition-all duration-300 cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-txt-secondary">{displayLabel}</span>
        <div className="w-8 h-8 rounded-full bg-bg-page border border-border-custom flex items-center justify-center text-txt-secondary group-hover:bg-brand-indigo-muted/30 group-hover:border-brand-indigo/20 transition-all duration-300">
          <Icon size={15} className={hoverColor === 'teal' ? 'text-ai-teal' : 'text-brand-indigo'} />
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <span className="text-2xl font-bold tracking-tight text-txt-primary">
          {value}
        </span>
        {delta && (
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${deltaColor}`}>
            {isIncrease ? '↑' : '↓'} {delta}
          </span>
        )}
      </div>

      {description && (
        <p className="mt-2 text-[11px] text-txt-tertiary font-normal">
          {description}
        </p>
      )}

      {/* Subtle left hover accent indicator */}
      <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${hoverColor === 'teal' ? 'bg-ai-teal' : 'bg-brand-indigo'} transform scale-y-0 group-hover:scale-y-100 transition-transform duration-300 origin-top`} />
    </motion.div>
  )
}
export default MetricCard
