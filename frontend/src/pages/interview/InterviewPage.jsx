import { useState, useEffect, useCallback } from 'react'
import { startInterview, startInterviewFromResume } from '../../api/interview'
import InterviewWorkspace from '../../components/interview/InterviewWorkspace'
import toast from 'react-hot-toast'

export default function InterviewPage() {
  const [role, setRole] = useState('Software Engineer')
  const [difficulty, setDifficulty] = useState(5)
  const [trainingMode, setTrainingMode] = useState('adaptive')
  const [persona, setPersona] = useState('balanced')
  const [useResume, setUseResume] = useState(true)
  const [session, setSession] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!session) return
    const handler = (e) => {
      e.preventDefault()
      e.returnValue = 'Interview in progress. Are you sure you want to leave?'
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [session])

  const handleStart = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = useResume
        ? await startInterviewFromResume({ role, difficulty, training_mode: trainingMode, interviewer_persona: persona })
        : await startInterview({ role, difficulty, training_mode: trainingMode, interviewer_persona: persona })
      setSession(data)
      toast.success('Interview started!')
    } catch (err) {
      console.error('Failed to start interview:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to start interview')
      toast.error('Failed to start interview')
    } finally {
      setIsLoading(false)
    }
  }

  const handleEnd = useCallback(() => {
    if (window.confirm('Interview in progress. Are you sure you want to leave?')) {
      setSession(null)
    }
  }, [])

  if (session) {
    return (
      <div className="min-h-screen bg-gray-50">
        <InterviewWorkspace session={session} onEnd={handleEnd} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">AI Interview</h1>

        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-300 rounded-lg text-red-700">
            {error}
            <button onClick={() => setError(null)} className="ml-4 text-sm underline">Dismiss</button>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Interview Setup</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <input type="text" value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Software Engineer" className="w-full p-2 border border-gray-200 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty (1-10)</label>
              <input type="number" value={difficulty} onChange={e => setDifficulty(Number(e.target.value))} min="1" max="10" className="w-full p-2 border border-gray-200 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Training Mode</label>
              <select value={trainingMode} onChange={e => setTrainingMode(e.target.value)} className="w-full p-2 border border-gray-200 rounded-lg">
                <option value="adaptive">Adaptive</option>
                <option value="weak_area_only">Weak Area Only</option>
                <option value="domain_specific">Domain Specific</option>
                <option value="behavioral_only">Behavioral Only</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Persona</label>
              <select value={persona} onChange={e => setPersona(e.target.value)} className="w-full p-2 border border-gray-200 rounded-lg">
                <option value="balanced">Balanced</option>
                <option value="strict">Strict</option>
                <option value="technical">Technical</option>
                <option value="friendly">Friendly</option>
                <option value="behavioral">Behavioral</option>
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="flex items-center cursor-pointer">
              <input type="checkbox" checked={useResume} onChange={e => setUseResume(e.target.checked)} className="mr-2" />
              <span className="text-sm">Use my uploaded resume for interview context</span>
            </label>
          </div>
          <button onClick={handleStart} disabled={isLoading} className="mt-6 w-full bg-blue-600 text-white py-2.5 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {isLoading ? 'Starting...' : 'Start Interview'}
          </button>
        </div>
      </div>
    </div>
  )
}
