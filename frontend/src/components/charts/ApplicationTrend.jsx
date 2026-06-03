import React from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-bg-elevated border border-border-hover-custom p-3 rounded-lg shadow-xl text-xs space-y-1.5 font-sans">
        <p className="font-semibold text-txt-primary">{label}</p>
        {payload.map((item, idx) => (
          <div key={idx} className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-txt-secondary">{item.name}:</span>
            <span className="font-bold text-txt-primary">{item.value}</span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export const ApplicationTrend = ({ data }) => {
  // Fallback seed data if not provided
  const defaultData = [
    { name: 'Mon', Applications: 12, Hires: 2 },
    { name: 'Tue', Applications: 19, Hires: 3 },
    { name: 'Wed', Applications: 15, Hires: 1 },
    { name: 'Thu', Applications: 28, Hires: 5 },
    { name: 'Fri', Applications: 22, Hires: 4 },
    { name: 'Sat', Applications: 8, Hires: 0 },
    { name: 'Sun', Applications: 14, Hires: 2 },
  ]

  const chartData = data && data.length > 0 ? data : defaultData

  return (
    <div className="w-full h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-semibold text-txt-primary">Application Volume</h4>
          <span className="text-[11px] text-txt-tertiary">Last 7 days</span>
        </div>
        {/* Custom Legend */}
        <div className="flex items-center space-x-4 text-xs font-medium">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-brand-indigo" />
            <span className="text-txt-secondary">Applications Received</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-ai-teal" />
            <span className="text-txt-secondary">Hired</span>
          </div>
        </div>
      </div>

      <div className="w-full h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="colorApplications" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#4F46E5" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorHires" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0D9488" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#0D9488" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1F2D45" strokeDasharray="3 3" opacity={0.4} vertical={false} />
            <XAxis
              dataKey="name"
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
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="Applications"
              name="Applications Received"
              stroke="#4F46E5"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorApplications)"
              activeDot={{ r: 4, strokeWidth: 0, fill: '#4F46E5' }}
            />
            <Area
              type="monotone"
              dataKey="Hires"
              name="Hired"
              stroke="#0D9488"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorHires)"
              activeDot={{ r: 4, strokeWidth: 0, fill: '#0D9488' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
export default ApplicationTrend
