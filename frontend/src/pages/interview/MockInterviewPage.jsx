import React, { useState, useEffect, useCallback } from 'react'
import { startMockInterview } from '../../api/mock_interview'
import { useLayoutStore } from '../../store/layoutStore'
import MockInterviewWorkspace from '../../components/interview/MockInterviewWorkspace'
import { MessageCircle, Settings, Play, Target, Shield, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function MockInterviewPage() {
  const [session, setSession] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const setFullscreen = useLayoutStore(state => state.setFullscreen)

  useEffect(() => {
    setFullscreen(!!session)
    return () => setFullscreen(false)
  }, [session, setFullscreen])
  
  // Practice form state
  const [config, setConfig] = useState({
    role: 'Software Engineer',
    difficulty: 5,
    training_mode: 'adaptive',
    interviewer_persona: 'balanced',
    interview_type: 'mixed',
    resume_source: 'none'
  })

  const handleStart = async (e) => {
    if (e) e.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      const data = await startMockInterview(config)
      setSession(data)
      toast.success('Mock Interview started!')
    } catch (err) {
      console.error('Failed to start mock interview:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to start interview')
      toast.error('Failed to start mock interview')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!session) return
    const handler = (e) => {
      e.preventDefault()
      e.returnValue = 'Interview in progress. Are you sure you want to leave?'
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [session])

  const handleEnd = useCallback(() => {
    if (window.confirm('Interview in progress. Are you sure you want to leave?')) {
      setSession(null)
    }
  }, [])

  if (session) {
    return (
      <div className="h-full min-h-0 bg-gray-50">
        <MockInterviewWorkspace session={session} onEnd={handleEnd} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="border-b border-gray-200 pb-4">
          <h1 className="text-3xl font-extrabold text-gray-950 flex items-center gap-2">
            <MessageCircle className="w-8 h-8 text-brand-indigo" />
            AI Mock Interview
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Practice for your next role in a safe, risk-free environment. Your performance here does not affect your official job applications.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-xl flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Setup Error</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Setup Form */}
        <form onSubmit={handleStart} className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <Settings className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-bold text-gray-800">Configure Practice Session</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">Target Role</label>
              <input
                type="text"
                value={config.role}
                onChange={e => setConfig({...config, role: e.target.value})}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo outline-none transition-all"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">Difficulty (1-10)</label>
              <input
                type="number"
                min="1" max="10"
                value={config.difficulty}
                onChange={e => setConfig({...config, difficulty: parseInt(e.target.value) || 5})}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo outline-none transition-all"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">Training Mode</label>
              <select
                value={config.training_mode}
                onChange={e => setConfig({...config, training_mode: e.target.value})}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:border-brand-indigo outline-none"
              >
                <option value="adaptive">Adaptive Learning</option>
                <option value="weak_area_only">Weak Area Drills</option>
                <option value="domain_specific">Domain Specific</option>
                <option value="behavioral_only">Behavioral Only</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">Interviewer Persona</label>
              <select
                value={config.interviewer_persona}
                onChange={e => setConfig({...config, interviewer_persona: e.target.value})}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:border-brand-indigo outline-none"
              >
                <option value="balanced">Balanced</option>
                <option value="friendly">Friendly Coach</option>
                <option value="strict">Strict / Pressure</option>
                <option value="technical">Technical Lead</option>
                <option value="behavioral">HR / Behavioral</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">Resume Context</label>
              <select
                value={config.resume_source}
                onChange={e => setConfig({...config, resume_source: e.target.value})}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-sm focus:border-brand-indigo outline-none"
              >
                <option value="none">No Resume (Blind Interview)</option>
                <option value="existing">Use Existing Resume</option>
              </select>
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 bg-brand-indigo hover:bg-brand-indigo-hover text-white px-6 py-2.5 rounded-lg font-bold text-sm transition-all shadow-sm disabled:opacity-50"
            >
              {isLoading ? (
                <>Starting...</>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Start Practice
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
