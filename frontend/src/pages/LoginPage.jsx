import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuthStore } from '../store/authStore'
import { login, register } from '../api/auth'
import { Eye, EyeOff, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export const LoginPage = () => {
  const navigate = useNavigate()
  const { setAuth, isAuthenticated, role } = useAuthStore()
  
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // If already logged in, redirect to correct dashboard
  useEffect(() => {
    if (isAuthenticated && role) {
      redirectToDashboard(role)
    }
  }, [isAuthenticated, role])

  const redirectToDashboard = (userRole) => {
    const normRole = (userRole || '').toLowerCase()
    if (normRole === 'candidate') {
      navigate('/dashboard/candidate')
    } else if (normRole === 'hr' || normRole === 'admin') {
      navigate('/dashboard/hr')
    } else if (normRole === 'manager') {
      navigate('/dashboard/manager')
    } else if (normRole === 'employee') {
      navigate('/dashboard/employee')
    } else {
      navigate('/dashboard/candidate') // Fallback
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!username || username.trim().length < 3) {
      setError('Username must be at least 3 characters')
      return
    }
    if (!password || password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setIsLoading(true)
    try {
      if (isLogin) {
        // Log in
        const data = await login(username.trim(), password)
        setAuth(data.access_token, data.has_resume)
        toast.success(`Welcome back, ${data.username}!`)
        redirectToDashboard(data.role)
      } else {
        // Register candidate
        const data = await register(username.trim(), password)
        setAuth(data.access_token, false)
        toast.success('Account created successfully!')
        redirectToDashboard(data.role)
      }
    } catch (err) {
      console.error(err)
      const msg = err.response?.data?.detail || 'Authentication failed. Please check credentials.'
      setError(msg)
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-bg-page w-full text-txt-primary select-none overflow-hidden">
      
      {/* Left Panel - Dynamic Premium Branding (60% width) */}
      <div className="hidden lg:flex flex-col justify-between w-3/5 p-16 relative bg-gradient-to-tr from-bg-page via-bg-page to-brand-indigo-muted/30 border-r border-border-custom">
        {/* Glow effect in background */}
        <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-brand-indigo/10 rounded-full blur-[120px] pointer-events-none" />
        
        {/* Logo and Tagline */}
        <div className="z-10">
          <div className="flex items-center space-x-3">
            <span className="w-10 h-10 rounded-lg bg-brand-indigo flex items-center justify-center text-white font-extrabold text-xl shadow-lg shadow-brand-indigo/20">
              TF
            </span>
            <span className="text-2xl font-bold tracking-tight text-txt-primary">
              TalentForge <span className="text-brand-indigo">AI</span>
            </span>
          </div>
          <p className="text-txt-secondary text-sm font-medium mt-2">
            Hire smarter. Grow faster.
          </p>
        </div>

        {/* Dynamic Animated Mesh SVG */}
        <div className="absolute inset-0 flex items-center justify-center opacity-60 z-0">
          <svg className="w-4/5 h-4/5 text-border-custom/50" viewBox="0 0 100 100" fill="none">
            <motion.path
              d="M10,50 Q30,20 50,50 T90,50"
              stroke="currentColor"
              strokeWidth="0.2"
              fill="none"
              animate={{ d: ["M10,50 Q30,20 50,50 T90,50", "M10,50 Q30,80 50,50 T90,50", "M10,50 Q30,20 50,50 T90,50"] }}
              transition={{ repeat: Infinity, duration: 10, ease: "easeInOut" }}
            />
            <motion.path
              d="M20,30 Q50,70 80,30"
              stroke="currentColor"
              strokeWidth="0.15"
              fill="none"
              animate={{ d: ["M20,30 Q50,70 80,30", "M20,30 Q50,10 80,30", "M20,30 Q50,70 80,30"] }}
              transition={{ repeat: Infinity, duration: 8, ease: "easeInOut" }}
            />
            <circle cx="50" cy="50" r="2" fill="currentColor" opacity="0.5" />
            <circle cx="30" cy="20" r="1.5" fill="currentColor" opacity="0.3" />
            <circle cx="70" cy="80" r="1.5" fill="currentColor" opacity="0.3" />
          </svg>
        </div>

        {/* Feature list */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="space-y-6 z-10"
        >
          <h2 className="text-xl font-semibold tracking-tight text-txt-primary">
            Intelligent Talent Operations Suite
          </h2>
          <div className="space-y-4">
            {[
              'AI-powered candidate scoring with explainability',
              'End-to-end hiring lifecycle management',
              'Real-time workforce intelligence dashboard',
            ].map((text, i) => (
              <div key={i} className="flex items-center space-x-3 text-sm text-txt-secondary">
                <CheckCircle size={18} className="text-ai-teal flex-shrink-0" />
                <span>{text}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Footer */}
        <div className="text-xs text-txt-tertiary z-10">
          © 2026 TalentForge AI. All rights reserved. Professional Grade ATS & HRMS.
        </div>
      </div>

      {/* Right Panel - Frosted Login Form (40% width) */}
      <div className="w-full lg:w-2/5 flex flex-col items-center justify-center p-8 bg-bg-surface border-l border-border-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="w-full max-w-[380px] bg-bg-elevated border border-border-hover-custom/60 rounded-2xl p-8 shadow-2xl relative overflow-hidden"
        >
          {/* Form Header */}
          <div className="text-center mb-6">
            <h3 className="text-xl font-bold tracking-tight text-txt-primary">
              Welcome back
            </h3>
            <p className="text-xs text-txt-secondary mt-1">
              Sign in to your workspace
            </p>
          </div>

          {/* Toggle Switch */}
          <div className="flex bg-bg-page border border-border-custom rounded-lg p-1 mb-6 relative">
            <button
              type="button"
              onClick={() => { setIsLogin(true); setError(''); }}
              className={`flex-1 text-center py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                isLogin ? 'bg-brand-indigo text-white shadow' : 'text-txt-secondary hover:text-txt-primary'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsLogin(false); setError(''); }}
              className={`flex-1 text-center py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                !isLogin ? 'bg-brand-indigo text-white shadow' : 'text-txt-secondary hover:text-txt-primary'
              }`}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Username Input */}
            <div className="space-y-1">
              <label className="block text-xs font-medium text-txt-secondary">
                Username
              </label>
              <input
                type="text"
                disabled={isLoading}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. recruit_lead"
                className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo rounded-lg px-3 py-2 text-sm text-txt-primary outline-none transition-colors disabled:opacity-50"
              />
            </div>

            {/* Password Input */}
            <div className="space-y-1 relative">
              <label className="block text-xs font-medium text-txt-secondary">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  disabled={isLoading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo rounded-lg pl-3 pr-10 py-2 text-sm text-txt-primary outline-none transition-colors disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-txt-secondary hover:text-txt-primary cursor-pointer"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-9 bg-brand-indigo hover:bg-brand-indigo-hover active:scale-[0.98] text-white text-xs font-semibold rounded-lg flex items-center justify-center cursor-pointer transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : isLogin ? (
                'Sign In'
              ) : (
                'Create Candidate Account'
              )}
            </button>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-xs font-medium text-danger-primary text-center pt-2"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

          </form>

          {/* Seeding credentials tip */}
          {isLogin && (
            <div className="mt-6 pt-4 border-t border-border-custom/50 text-[10px] text-txt-tertiary leading-relaxed">
              <span className="font-semibold text-txt-secondary block mb-1">Standard Demo Accounts:</span>
              <ul className="list-disc pl-3.5 space-y-0.5">
                <li>Candidates: register custom or check DB users</li>
                <li>HR: check database roles / register via admin panel</li>
              </ul>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
export default LoginPage
