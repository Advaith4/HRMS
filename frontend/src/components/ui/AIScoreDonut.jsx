import React, { useEffect, useState } from 'react'

export const AIScoreDonut = ({ score = 0 }) => {
  const targetScore = Math.max(0, Math.min(100, score))
  const [currentScore, setCurrentScore] = useState(0)

  useEffect(() => {
    // Reset and animate
    setCurrentScore(0)
    
    let startTimestamp = null
    const duration = 1200 // 1.2s matching the stroke animation
    
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp
      const progress = Math.min((timestamp - startTimestamp) / duration, 1)
      
      // Ease out quad
      const easeProgress = progress * (2 - progress)
      
      setCurrentScore(Math.floor(easeProgress * targetScore))
      
      if (progress < 1) {
        window.requestAnimationFrame(step)
      }
    }
    
    window.requestAnimationFrame(step)
  }, [score, targetScore])

  // Determine colors based on current score
  const getColors = (val) => {
    if (val >= 70) return { stroke: '#10B981', text: 'text-success-primary' }
    if (val >= 40) return { stroke: '#F59E0B', text: 'text-warning-custom' }
    return { stroke: '#EF4444', text: 'text-danger-primary' }
  }

  const { stroke, text } = getColors(currentScore)

  // SVG parameters
  const size = 200
  const radius = 80
  const strokeWidth = 14
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (currentScore / 100) * circumference

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div className="relative w-[200px] h-[200px]">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
          {/* Background Ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="#E2E8F0"
            strokeWidth={strokeWidth}
          />
          {/* Active Score Ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="donut-segment"
          />
        </svg>
        {/* Centered Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className={`text-4xl font-bold tracking-tighter ${text}`}>
            {currentScore}
          </span>
          <span className="text-[11px] font-medium text-txt-secondary uppercase tracking-wider mt-1">
            AI Fit Score
          </span>
        </div>
      </div>
    </div>
  )
}
export default AIScoreDonut
