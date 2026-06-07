import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuthStore } from '../store/authStore'
import { login, register } from '../api/auth'
import { Eye, EyeOff, ShieldCheck, Lock, X, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import heroImage from '../assets/hero.png'

export const LoginPage = () => {
  const navigate = useNavigate()
  const { setAuth, isAuthenticated, role } = useAuthStore()
  
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Demo Modal State
  const [showDemoModal, setShowDemoModal] = useState(false)

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
    if (e) e.preventDefault()
    setError('')
    
    if (!username || username.trim().length < 3) {
      setError('Username or Email must be at least 3 characters')
      return
    }
    if (!password || password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setIsLoading(true)
    try {
      if (isLogin) {
        const data = await login(username.trim(), password)
        setAuth(data.access_token, data.has_resume)
        toast.success(`Welcome back, ${data.username}!`)
        redirectToDashboard(data.role)
      } else {
        const data = await register(username.trim(), password)
        setAuth(data.access_token, false)
        toast.success('Account created successfully!')
        redirectToDashboard(data.role)
      }
    } catch (err) {
      console.error(err)
      const msg = err.response?.data?.detail || 'Authentication failed. Please check your credentials.'
      setError(msg)
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  // Auto-fill and submit helper
  const handleDemoAutofill = async (demoUser, demoPass) => {
    setShowDemoModal(false)
    setUsername(demoUser)
    setPassword(demoPass)
    setError('')
    setIsLoading(true)
    try {
      const data = await login(demoUser, demoPass)
      setAuth(data.access_token, data.has_resume)
      toast.success(`Logged in as ${data.username}`)
      redirectToDashboard(data.role)
    } catch (err) {
      console.error(err)
      const msg = err.response?.data?.detail || 'Demo login failed.'
      setError(msg)
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-row min-h-screen w-full bg-bg-page text-txt-primary font-sans select-none overflow-x-hidden">
      
      {/* LEFT PANEL (65%) — Background Image with Warm Color Tone Overlay */}
      <div className="w-[60%] xl:w-[65%] hidden lg:block relative overflow-hidden bg-[#2e130a]">
        
        {/* Background Image */}
        <img 
          src={heroImage} 
          alt="Workforce Showcase" 
          className="absolute inset-0 w-full h-full object-cover"
        />
        
        {/* Warm Overlay to harmonize text with the warm orange background */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#150702]/95 via-[#2e130a]/40 to-[#2e130a]/15 backdrop-blur-[0.5px]" />
        
        {/* Branding & Overlay Copy */}
        <div className="absolute bottom-20 left-20 z-10 max-w-2xl">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="space-y-5"
          >
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-brand-indigo flex items-center justify-center text-white font-extrabold text-lg shadow-md shadow-brand-indigo/35">
                TF
              </div>
              <span className="text-2xl font-bold tracking-tight text-white">
                TalentForge <span className="text-slate-300 font-normal">HRMS</span>
              </span>
            </div>

            {/* Strategic HR Messaging */}
            <h1 className="text-3xl lg:text-4xl xl:text-5xl font-extrabold tracking-tight text-white leading-tight">
              Build Better Teams.<br />
              Manage Smarter Workforces.
            </h1>
            
            <p className="text-slate-200/90 text-sm lg:text-base font-normal leading-relaxed max-w-lg">
              A unified enterprise platform for recruitment, employee lifecycle tracking, upskilling modules, and payroll analytics.
            </p>
          </motion.div>
        </div>

        {/* Security Info Panel */}
        <div className="absolute bottom-8 left-20 z-10 flex gap-5 text-[11px] text-slate-400 font-medium tracking-wide">
          <span className="flex items-center gap-1.5"><ShieldCheck size={13} className="text-emerald-500" /> RBAC Compliant</span>
          <span className="flex items-center gap-1.5"><Lock size={13} className="text-emerald-500" /> AES-256 Encryption</span>
        </div>

      </div>

      {/* RIGHT PANEL (35%) — Clean Authentication Panel */}
      <div className="w-full lg:w-[40%] xl:w-[35%] flex flex-col justify-center items-center p-6 sm:p-8 lg:p-12 bg-bg-surface relative min-h-screen lg:min-h-0 border-l border-border-custom">
        
        {/* Login Card Form Container */}
        <div className="w-full max-w-[360px] my-auto py-8">
          
          {/* Logo Branding (Mobile only) */}
          <div className="flex lg:hidden items-center space-x-2.5 mb-8">
            <div className="w-8 h-8 rounded-lg bg-brand-indigo flex items-center justify-center text-white font-extrabold text-base shadow-md shadow-brand-indigo/35">
              TF
            </div>
            <span className="text-lg font-bold tracking-tight text-txt-primary">
              TalentForge <span className="text-txt-secondary font-normal">HRMS</span>
            </span>
          </div>

          {/* Heading */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-txt-primary tracking-tight">
              {isLogin ? 'Sign In' : 'Create Account'}
            </h2>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              {isLogin 
                ? 'Welcome back. Enter your workspace credentials to access your secure portal.' 
                : 'Set up your details below to request access to the company database.'}
            </p>
          </div>

          {/* Input Fields & Submit */}
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Username/Email Input */}
            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-txt-secondary">Username or Email</label>
              <input
                type="text"
                disabled={isLoading}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3.5 py-2 text-sm text-txt-primary bg-bg-surface border border-border-custom rounded-lg focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo disabled:opacity-50 transition"
                placeholder="e.g. employee.name"
              />
            </div>

            {/* Password Input */}
            <div className="flex flex-col space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-slate-700">Password</label>
                <button
                  type="button"
                  onClick={() => toast.error('Contact your IT or HR Administrator to request a password reset.')}
                  className="text-xs text-brand-indigo hover:text-brand-indigo-hover font-semibold transition"
                >
                  Forgot Password?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  disabled={isLoading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm text-txt-primary bg-bg-surface border border-border-custom rounded-lg focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo disabled:opacity-50 transition pr-10"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition cursor-pointer"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Actions (Remember Me) */}
            <div className="flex items-center text-xs pt-0.5">
              <label className="flex items-center gap-2 text-txt-secondary cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 bg-bg-surface border border-border-custom rounded focus:ring-0 accent-brand-indigo cursor-pointer"
                />
                <span className="font-medium">Remember me on this device</span>
              </label>
            </div>

            {/* Sign In CTA Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-bold rounded-lg flex items-center justify-center cursor-pointer transition disabled:opacity-50 shadow-sm border border-transparent"
            >
              {isLoading ? (
                <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : isLogin ? (
                'Sign In'
              ) : (
                'Request Account'
              )}
            </button>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-xs font-semibold text-red-500 text-center pt-2 leading-relaxed"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

          </form>

          {/* Toggle register/login links */}
          <div className="text-xs text-center text-slate-500 mt-5">
            {isLogin ? (
              <>
                New to TalentForge?{' '}
                <button
                  type="button"
                  onClick={() => { setIsLogin(false); setError(''); }}
                  className="text-brand-indigo hover:underline font-semibold"
                >
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => { setIsLogin(true); setError(''); }}
                  className="text-brand-indigo hover:underline font-semibold"
                >
                  Sign in
                </button>
              </>
            )}
          </div>

          {/* View Demo Access Link */}
          {isLogin && (
            <div className="mt-8 text-center border-t border-slate-100 pt-6">
              <button
                type="button"
                onClick={() => setShowDemoModal(true)}
                className="text-xs text-slate-400 hover:text-slate-600 transition cursor-pointer"
              >
                Need demo system access? <span className="underline font-semibold text-slate-500 hover:text-slate-700">View Credentials</span>
              </button>
            </div>
          )}

        </div>

        {/* Outer Footer */}
        <div className="text-center w-full text-[10px] text-slate-400/80">
          © 2026 TalentForge. All rights reserved. Secure Corporate Gateway.
        </div>

      </div>

      {/* DEMO CREDENTIALS MODAL */}
      <AnimatePresence>
        {showDemoModal && (
          <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-bg-surface rounded-2xl border border-border-custom p-6 max-w-sm w-full shadow-2xl relative"
            >
              {/* Close Button */}
              <button
                type="button"
                onClick={() => setShowDemoModal(false)}
                className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X size={18} />
              </button>

              <div className="flex items-center gap-2 mb-4 text-[#EA580C]">
                <AlertCircle size={20} />
                <h3 className="text-base font-bold text-txt-primary">Demo System Access</h3>
              </div>

              <p className="text-xs text-slate-500 mb-4 leading-normal">
                Click any profile button below to automatically autofill standard demo credentials and log in to that role's workspace.
              </p>

              {/* Roles List */}
              <div className="space-y-3">
                
                <div className="p-3 rounded-xl border border-border-custom bg-bg-page flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-txt-primary">HR Administrator</div>
                    <div className="text-[10px] text-txt-tertiary">User: demo_hr | Pass: Pass123!</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDemoAutofill('demo_hr', 'Pass123!')}
                    className="px-2.5 py-1 rounded-lg bg-brand-indigo hover:bg-brand-indigo-hover text-white text-[10px] font-bold shadow-sm"
                  >
                    Login
                  </button>
                </div>

                <div className="p-3 rounded-xl border border-border-custom bg-bg-page flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-txt-primary">Department Manager</div>
                    <div className="text-[10px] text-txt-tertiary">User: demo_manager | Pass: Pass123!</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDemoAutofill('demo_manager', 'Pass123!')}
                    className="px-2.5 py-1 rounded-lg bg-brand-indigo hover:bg-brand-indigo-hover text-white text-[10px] font-bold shadow-sm"
                  >
                    Login
                  </button>
                </div>

                <div className="p-3 rounded-xl border border-border-custom bg-bg-page flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-txt-primary">Staff Employee</div>
                    <div className="text-[10px] text-txt-tertiary">User: demo_employee | Pass: Pass123!</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDemoAutofill('demo_employee', 'Pass123!')}
                    className="px-2.5 py-1 rounded-lg bg-brand-indigo hover:bg-brand-indigo-hover text-white text-[10px] font-bold shadow-sm"
                  >
                    Login
                  </button>
                </div>

              </div>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  )
}

export default LoginPage
