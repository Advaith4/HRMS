import React, { useEffect, useState } from 'react'

export const SkillGapRadial = ({ percent = 0 }) => {
  const targetPercent = Math.max(0, Math.min(100, percent))
  const [currentPercent, setCurrentPercent] = useState(0)

  useEffect(() => {
    setCurrentPercent(0)
    const duration = 1000
    let startTimestamp = null
    
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp
      const progress = Math.min((timestamp - startTimestamp) / duration, 1)
      const easeProgress = progress * (2 - progress) // Ease out
      setCurrentPercent(Math.floor(easeProgress * targetPercent))
      if (progress < 1) {
        window.requestAnimationFrame(step)
      }
    }
    
    window.requestAnimationFrame(step)
  }, [percent, targetPercent])

  const size = 180
  const radius = 64
  const strokeWidth = 10
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (currentPercent / 100) * circumference

  return (
    <div className="flex items-center justify-center p-4">
      <div className="relative w-[180px] h-[180px]">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="#1F2D45"
            strokeWidth={strokeWidth}
          />
          {/* Dynamic Teal Progress */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="#0D9488"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
          />
        </svg>
        {/* Centered details */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-3xl font-bold tracking-tight text-txt-primary">
            {currentPercent}%
          </span>
          <span className="text-[10px] font-semibold text-ai-teal uppercase tracking-widest mt-0.5">
            Gap Closed
          </span>
        </div>
      </div>
    </div>
  )
}
export default SkillGapRadial
