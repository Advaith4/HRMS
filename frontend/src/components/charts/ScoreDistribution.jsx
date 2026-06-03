import React from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-bg-elevated border border-border-hover-custom p-3 rounded-lg shadow-xl text-xs space-y-1.5 font-sans">
        <p className="font-semibold text-txt-primary">{payload[0].payload.range}</p>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-indigo" />
          <span className="text-txt-secondary">Candidates:</span>
          <span className="font-bold text-txt-primary">{payload[0].value}</span>
        </div>
      </div>
    )
  }
  return null
}

export const ScoreDistribution = ({ data }) => {
  // Fallback seed data representing score distribution
  const defaultData = [
    { range: '0–20', count: 4, color: '#EF4444' }, // Red for low score
    { range: '20–40', count: 12, color: '#F59E0B' }, // Amber
    { range: '40–60', count: 28, color: '#3B82F6' }, // Blue
    { range: '60–80', count: 45, color: '#4F46E5' }, // Indigo
    { range: '80–100', count: 21, color: '#14B8A6' }, // Teal
  ]

  const chartData = data && data.length > 0 ? data : defaultData

  return (
    <div className="w-full h-full">
      <div className="mb-4">
        <h4 className="text-base font-semibold text-txt-primary">Candidate Score Distribution</h4>
        <span className="text-[11px] text-txt-tertiary">Real-time candidate fit profiles</span>
      </div>

      <div className="w-full h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
            <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" opacity={0.8} vertical={false} />
            <XAxis
              dataKey="range"
              stroke="#475569"
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              dy={10}
            />
            <YAxis
              stroke="#475569"
              tick={{ fill: '#94A3B8', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F1F5F9', opacity: 0.4 }} />
            <Bar
              dataKey="count"
              radius={[4, 4, 0, 0]}
              maxBarSize={48}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color || '#4F46E5'} 
                  fillOpacity={0.85}
                  stroke={entry.color || '#4F46E5'}
                  strokeWidth={1}
                  className="hover:opacity-100 hover:stroke-[2px] transition-all cursor-pointer"
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
export default ScoreDistribution
