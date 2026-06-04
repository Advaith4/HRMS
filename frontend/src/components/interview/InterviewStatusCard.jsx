import React from 'react'
import { Camera, Monitor, Mic, Clock, MessageSquare, Hash } from 'lucide-react'

export default function InterviewStatusCard({
  questionCount,
  duration,
  micStatus,
  cameraStatus,
  screenShareStatus,
}) {
  const statusDot = (status) => {
    if (status === 'active') return <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
    if (status === 'denied' || status === 'unavailable' || status === 'error') return <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
    return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />
  }

  const statusLabel = (status) => {
    if (status === 'active') return 'Active'
    if (status === 'denied') return 'Denied'
    if (status === 'unavailable') return 'Unavailable'
    if (status === 'error') return 'Error'
    if (status === 'requesting') return 'Requesting...'
    return 'Off'
  }

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  const rows = [
    { icon: MessageSquare, label: 'Questions', value: questionCount },
    { icon: Clock, label: 'Duration', value: formatTime(duration) },
    { icon: Mic, label: 'Microphone', value: statusLabel(micStatus), dot: statusDot(micStatus) },
    { icon: Camera, label: 'Camera', value: statusLabel(cameraStatus), dot: statusDot(cameraStatus) },
    { icon: Monitor, label: 'Screen Share', value: statusLabel(screenShareStatus), dot: statusDot(screenShareStatus) },
  ]

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Session Status</h3>
      {rows.map((r, i) => (
        <div key={i} className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <r.icon className="w-4 h-4" />
            <span>{r.label}</span>
          </div>
          <div className="flex items-center gap-1.5 text-sm font-medium text-gray-800">
            {r.dot}
            <span>{r.value}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
