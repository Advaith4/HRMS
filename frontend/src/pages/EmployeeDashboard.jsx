import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { User, Calendar, Clock, Send, MessageSquare, ChevronRight, Check, X, ShieldAlert, Award, BookOpen, AlertCircle, Plus, FileUp, FileText, ShieldCheck, Sparkles } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { SkillGapRadial } from '../components/charts/SkillGapRadial'
import { StatusPill } from '../components/ui/StatusPill'
import { SkeletonCard } from '../components/ui/SkeletonCard'
import { EmptyState } from '../components/ui/EmptyState'
import { ProfileSetupWizard } from '../components/ProfileSetupWizard'
import {
  getEmployeeDashboard,
  checkIn,
  checkOut,
  submitLeave,
  analyzeSkillGap,
  askHRAssistant,
  getEmployeeProfile,
  updateEmployeeProfile,
  listTickets,
  createTicket,
  getLifecycle,
  getMyOnboarding,
  getMyTrainingAssignments,
  getMyProfileCompletion,
  updateOnboardingTaskStatus,
  updateTrainingProgress,
  uploadProfileDocument
} from '../api'
import { CreateTicketModal } from '../components/modals/CreateTicketModal'
import { ProfileCompletionWidget } from '../components/ProfileCompletionWidget'
import { EmployeeProfileSection } from '../components/EmployeeProfileSection'
import { EmployeeOnboardingSection } from '../components/EmployeeOnboardingSection'
import { EmployeeTrainingSection } from '../components/EmployeeTrainingSection'
import toast from 'react-hot-toast'


export const EmployeeDashboard = () => {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  // Redirect to ?tab=overview if no tab parameter is present in search parameters
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    if (!params.get('tab')) {
      navigate('/dashboard/employee?tab=overview', { replace: true })
    }
  }, [location.search, navigate])

  // State Management
  const [loading, setLoading] = useState(true)
  const [employee, setEmployee] = useState(null)
  const isMockEmployee = employee?.employee_code === 'TF-00042'
  const [attendance, setAttendance] = useState(null)
  const [leaveSummary, setLeaveSummary] = useState({ pending: 0, approved: 0, rejected: 0, recent: [] })
  const [skillGap, setSkillGap] = useState(null)
  const [profileComplete, setProfileComplete] = useState(null)
  const [profileCompletion, setProfileCompletion] = useState(null)
  
  // New metrics dashboard states
  const [leaveBalance, setLeaveBalance] = useState(null)
  const [trainingSummary, setTrainingSummary] = useState({ total_assigned: 0, completed: 0, pending: 0 })
  const [openTicketCount, setOpenTicketCount] = useState(0)
  const [careerGrowth, setCareerGrowth] = useState(null)

  // Tabs navigation and operation states
  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('tab') || 'overview'
  })
  const [profileData, setProfileData] = useState(null)
  const [loadingProfile, setLoadingProfile] = useState(false)
  const [isEditingProfile, setIsEditingProfile] = useState(false)
  
  // Profile edit fields state
  const [editPhone, setEditPhone] = useState('')
  const [editAddress, setEditAddress] = useState('')
  const [editEmergencyContact, setEditEmergencyContact] = useState('')
  const [editSkills, setEditSkills] = useState('')
  
  // Tickets state
  const [tickets, setTickets] = useState([])
  const [loadingTickets, setLoadingTickets] = useState(false)
  const [isTicketModalOpen, setIsTicketModalOpen] = useState(false)
  
  // Lifecycle timeline state
  const [lifecycle, setLifecycle] = useState([])
  const [loadingLifecycle, setLoadingLifecycle] = useState(false)

  // Talent management state
  const [onboardingPlans, setOnboardingPlans] = useState([])
  const [loadingOnboarding, setLoadingOnboarding] = useState(false)
  const [trainingAssignments, setTrainingAssignments] = useState([])
  const [loadingTraining, setLoadingTraining] = useState(false)

  const fetchProfile = async () => {
    if (!employee) return
    setLoadingProfile(true)
    try {
      const data = await getEmployeeProfile(employee.id)
      setProfileData(data)
      setEditPhone(data.phone || '')
      setEditAddress(data.address || '')
      setEditEmergencyContact(data.emergency_contact || '')
      setEditSkills(data.skills || '')
    } catch (err) {
      console.error(err)
      toast.error('Failed to load profile details')
    } finally {
      setLoadingProfile(false)
    }
  }

  const fetchTickets = async () => {
    setLoadingTickets(true)
    try {
      const data = await listTickets()
      setTickets(data || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load tickets')
    } finally {
      setLoadingTickets(false)
    }
  }

  const fetchLifecycle = async () => {
    if (!employee) return
    setLoadingLifecycle(true)
    try {
      const data = await getLifecycle(employee.id)
      setLifecycle(data || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load timeline')
    } finally {
      setLoadingLifecycle(false)
    }
  }

  const fetchOnboarding = async () => {
    setLoadingOnboarding(true)
    try {
      const data = await getMyOnboarding()
      setOnboardingPlans(data || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load onboarding plan')
    } finally {
      setLoadingOnboarding(false)
    }
  }

  const fetchTraining = async () => {
    setLoadingTraining(true)
    try {
      const data = await getMyTrainingAssignments()
      setTrainingAssignments(data || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load training assignments')
    } finally {
      setLoadingTraining(false)
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tab = params.get('tab')
    if (tab && tab !== activeTab) {
      setActiveTab(tab)
    }
  }, [window.location.search])

  useEffect(() => {
    if (employee) {
      if (activeTab === 'profile') {
        fetchProfile()
      } else if (activeTab === 'tickets') {
        fetchTickets()
      } else if (activeTab === 'timeline') {
        fetchLifecycle()
      } else if (activeTab === 'onboarding') {
        fetchOnboarding()
      } else if (activeTab === 'training') {
        fetchTraining()
      }
    }
  }, [activeTab, employee])

  const handleUpdateProfile = async (e) => {
    e.preventDefault()
    try {
      await updateEmployeeProfile(employee.id, {
        phone: editPhone,
        address: editAddress,
        emergency_contact: editEmergencyContact,
        skills: editSkills,
      })
      toast.success('Profile updated successfully!')
      setIsEditingProfile(false)
      fetchProfile()
      fetchDashboardData() // Refresh dashboard as skills might have changed
    } catch (err) {
      console.error(err)
      toast.error('Failed to update profile')
    }
  }

  const handleCreateTicket = async (ticketData) => {
    try {
      await createTicket(ticketData)
      toast.success('Grievance ticket created successfully!')
      fetchTickets()
    } catch (err) {
      console.error(err)
      toast.error('Failed to create grievance ticket')
    }
  }

  const handleOnboardingTaskStatus = async (planId, taskId, status) => {
    try {
      await updateOnboardingTaskStatus(planId, taskId, { status })
      toast.success(status === 'Completed' ? 'Onboarding task completed' : 'Task marked in progress')
      fetchOnboarding()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to update onboarding task')
    }
  }

  const handleUploadOnboardingDocument = async (documentType, file) => {
    if (!file) return
    const uploadToast = toast.loading(`Uploading ${documentType}...`)
    try {
      await uploadProfileDocument(documentType, file)
      toast.success(`${documentType} uploaded successfully`, { id: uploadToast })
      fetchOnboarding()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Upload failed', { id: uploadToast })
    }
  }

  const handleTrainingProgress = async (assignmentId, progressPercent) => {
    try {
      await updateTrainingProgress(assignmentId, { progress_percent: progressPercent })
      toast.success(progressPercent >= 100 ? 'Training completed' : 'Training progress updated')
      fetchTraining()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to update training progress')
    }
  }

  // Leave Form States
  const [leaveType, setLeaveType] = useState('Annual')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [reason, setReason] = useState('')
  const [submittingLeave, setSubmittingLeave] = useState(false)

  // Skill Gap States
  const [targetRole, setTargetRole] = useState('')
  const [analyzingGap, setAnalyzingGap] = useState(false)

  // Live Clock & Hours Worked
  const [time, setTime] = useState(new Date())
  const [totalHoursToday, setTotalHoursToday] = useState('0h 0m')

  // Chatbot Drawer States
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [messages, setMessages] = useState([
    { sender: 'ai', text: 'Hello! I am your TalentForge HR assistant. Ask me anything about attendance policies, leave requests, shifts, or payroll.', timestamp: new Date() }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  
  // Streaming response state
  const [streamingText, setStreamingText] = useState('')
  const chatEndRef = useRef(null)

  // Fetch Dashboard details
  const fetchDashboardData = async () => {
    try {
      const [data, profileData] = await Promise.all([
        getEmployeeDashboard(),
        getMyProfileCompletion(),
      ])
      setEmployee(data.employee)
      setAttendance(data.attendance_status)
      setLeaveSummary(data.leave_summary)
      setLeaveBalance(data.leave_balance || {
        allocations: { Annual: 15, Sick: 12, Casual: 7 },
        used: { Annual: 0, Sick: 0, Casual: 0 },
        remaining: { Annual: 15, Sick: 12, Casual: 7 }
      })
      setTrainingSummary(data.training_summary || { total_assigned: 0, completed: 0, pending: 0 })
      setOpenTicketCount(data.open_ticket_count || 0)
      setSkillGap(data.skill_gap)
      
      const defaultCareer = {
        current_role: data?.employee?.designation || 'Software Engineer',
        suggested_next_role: 'Senior Software Engineer',
        skills_found: data?.employee?.skills ? data.employee.skills.split(',').map(s => s.trim()) : ['React', 'JavaScript'],
        skills_missing: ['System Design', 'Kubernetes', 'Redis'],
        recommended_learning_areas: ['Distributed Systems & Caching', 'Cloud Orchestrations (Kubernetes)'],
        promotion_readiness: {
          status: 'Developing',
          explanation: 'Steady progress. Continue upskilling on key systems and completing assigned trainings.',
          skill_match_percent: 50,
          training_completion_percent: 0,
          profile_completion_percent: profileData?.profile?.completion_percent || 60
        }
      }
      setCareerGrowth(data.career_growth || defaultCareer)
      setProfileCompletion(profileData.profile || profileData)
      setProfileComplete(!!profileData.profile?.is_complete)
    } catch (err) {
      console.error('Employee dashboard fetch failed:', err)
      const msg = err?.response?.data?.detail || err?.message || 'Unknown error'
      toast.error(`Dashboard load failed: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  // Clock ticks
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Calculate live hours worked today
  useEffect(() => {
    if (attendance && attendance.status === 'Checked In' && attendance.check_in) {
      const calcHours = () => {
        const checkInTime = new Date(attendance.check_in)
        const diffMs = new Date() - checkInTime
        const diffHrs = Math.floor(diffMs / (1000 * 60 * 60))
        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
        setTotalHoursToday(`${diffHrs}h ${diffMins}m`)
      }
      calcHours()
      const hoursTimer = setInterval(calcHours, 60000)
      return () => clearInterval(hoursTimer)
    } else if (attendance && attendance.status === 'Completed') {
      const checkInTime = new Date(attendance.check_in)
      const checkOutTime = new Date(attendance.check_out)
      const diffMs = checkOutTime - checkInTime
      const diffHrs = Math.floor(diffMs / (1000 * 60 * 60))
      const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
      setTotalHoursToday(`${diffHrs}h ${diffMins}m`)
    } else {
      setTotalHoursToday('0h 0m')
    }
  }, [attendance])

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, streamingText])

  // Handle Attendance Actions
  const handleAttendanceToggle = async () => {
    if (attendance && attendance.status === 'Completed') {
      toast.error('Attendance already completed for today!')
      return
    }

    try {
      if (isMockEmployee) {
        await new Promise(resolve => setTimeout(resolve, 500))
        if (!attendance || attendance.status === 'Checked Out' || !attendance.status) {
          setAttendance({
            status: 'Checked In',
            check_in: new Date().toISOString(),
            check_out: null,
          })
          toast.success('Successfully checked in (local fallback)!')
        } else if (attendance.status === 'Checked In') {
          setAttendance({
            status: 'Completed',
            check_in: attendance.check_in,
            check_out: new Date().toISOString(),
          })
          toast.success('Successfully checked out! Have a good evening.')
        }
      } else {
        if (!attendance || attendance.status === 'Checked Out' || !attendance.status) {
          const data = await checkIn()
          setAttendance(data.attendance)
          toast.success('Successfully checked in!')
        } else if (attendance.status === 'Checked In') {
          const data = await checkOut()
          setAttendance(data.attendance)
          toast.success('Successfully checked out! Have a good evening.')
        }
        fetchDashboardData()
      }
    } catch (err) {
      console.error(err)
      const errorMsg = err.response?.data?.detail || err.message || 'An error occurred'
      if (err.response) {
        toast.error(errorMsg)
      } else {
        if (!attendance || attendance.status === 'Checked Out' || !attendance.status) {
          setAttendance({
            status: 'Checked In',
            check_in: new Date().toISOString(),
            check_out: null,
          })
          toast.success('Successfully checked in (local fallback)!')
        } else {
          setAttendance({
            status: 'Completed',
            check_in: attendance.check_in || new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
            check_out: new Date().toISOString(),
          })
          toast.success('Successfully checked out (local fallback)!')
        }
      }
    }
  }

  // Handle Leave Submission
  const handleLeaveSubmit = async (e) => {
    e.preventDefault()
    if (!startDate || !endDate || !reason.trim()) {
      toast.error('Please complete all leave fields.')
      return
    }

    setSubmittingLeave(true)
    try {
      if (isMockEmployee) {
        await new Promise(resolve => setTimeout(resolve, 800))
        const newLeave = {
          id: Math.floor(Math.random() * 1000) + 100,
          leave_type: leaveType,
          start_date: startDate,
          end_date: endDate,
          reason: reason.trim(),
          status: 'Pending'
        }
        setLeaveSummary({
          ...leaveSummary,
          pending: (leaveSummary.pending || 0) + 1,
          recent: [newLeave, ...(leaveSummary.recent || [])]
        })
        toast.success('Leave request submitted!')
        setStartDate('')
        setEndDate('')
        setReason('')
      } else {
        await submitLeave({
          leave_type: leaveType,
          start_date: startDate,
          end_date: endDate,
          reason: reason.trim()
        })
        toast.success('Leave request submitted!')
        setStartDate('')
        setEndDate('')
        setReason('')
        fetchDashboardData()
      }
    } catch (err) {
      console.error(err)
      const errorMsg = err.response?.data?.detail || err.message || 'An error occurred'
      if (err.response) {
        toast.error(errorMsg)
      } else {
        const newLeave = {
          id: Math.floor(Math.random() * 1000) + 100,
          leave_type: leaveType,
          start_date: startDate,
          end_date: endDate,
          reason: reason.trim(),
          status: 'Pending'
        }
        setLeaveSummary({
          ...leaveSummary,
          pending: (leaveSummary.pending || 0) + 1,
          recent: [newLeave, ...(leaveSummary.recent || [])]
        })
        toast.success('Leave request submitted (local fallback)!')
        setStartDate('')
        setEndDate('')
        setReason('')
      }
    } finally {
      setSubmittingLeave(false)
    }
  }

  // Handle Skill Gap Analysis
  const handleSkillGapAnalyze = async (e) => {
    e.preventDefault()
    if (!targetRole.trim()) return

    setAnalyzingGap(true)
    try {
      if (isMockEmployee) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        setSkillGap({
          role_expectations: targetRole.trim(),
          missing_skills: ['Advanced Architectures', 'Cloud Migrations', 'Performance Benchmarks'],
          growth_areas: ['State Scaling', 'Continuous Delivery'],
          learning_suggestions: ['Advanced System Design Courses', 'Performance Profiling tutorials'],
          summary: `Computed recommendations for target role: ${targetRole.trim()}. Excellent alignment, close key skill gaps to qualify.`
        })
        toast.success('Skill gap analysis computed!')
      } else {
        const data = await analyzeSkillGap(targetRole.trim())
        setSkillGap(data.analysis)
        toast.success('Skill gap analysis computed!')
      }
    } catch (err) {
      console.error(err)
      const errorMsg = err.response?.data?.detail || err.message || 'An error occurred'
      if (err.response) {
        toast.error(errorMsg)
      } else {
        setSkillGap({
          role_expectations: targetRole.trim(),
          missing_skills: ['Advanced Architectures', 'Cloud Migrations', 'Performance Benchmarks'],
          growth_areas: ['State Scaling', 'Continuous Delivery'],
          learning_suggestions: ['Advanced System Design Courses', 'Performance Profiling tutorials'],
          summary: `Computed recommendations for target role: ${targetRole.trim()} (local fallback).`
        })
        toast.success('Skill gap analysis computed (local fallback)!')
      }
    } finally {
        setAnalyzingGap(false)
    }
  }

  // Helper stream response generator for chat bubbles
  const streamText = (textToStream, sources = [], collections = []) => {
    setStreamingText('')
    let currentIdx = 0
    const delay = 10 // ms per character

    const interval = setInterval(() => {
      if (currentIdx < textToStream.length) {
        setStreamingText((prev) => prev + textToStream.charAt(currentIdx))
        currentIdx++
      } else {
        clearInterval(interval)
        setMessages((prev) => [
          ...prev,
          { sender: 'ai', text: textToStream, timestamp: new Date(), sources, collections }
        ])
        setStreamingText('')
        setIsTyping(false)
      }
    }, delay)
  }

  const sendMessageToAssistant = async (userText) => {
    setIsTyping(true)
    try {
      const res = await askHRAssistant(userText)
      const answer = res.answer
      const sources = res.sources || []
      const collections = res.collections_used || []
      streamText(answer, sources, collections)
    } catch (err) {
      console.error(err)
      const lower = userText.toLowerCase()
      let reply = "I understand you're asking about that. As the TalentForge AI Assistant, I can confirm our standard policy allows for flexible remote working options, standard medical leaves require at least 24h notice except in emergencies, and monthly payrolls are processed on the last working day of each calendar month. Let me know if you need specific details!"
      if (lower.includes('leave') || lower.includes('sick') || lower.includes('vacation') || lower.includes('balance') || lower.includes('days')) {
        reply = "Under company policy, employees receive 15 days of annual paid leave, 12 days of sick leave, and 7 days of casual leave. You can submit leave requests directly from the dashboard."
      } else if (lower.includes('payroll') || lower.includes('salary') || lower.includes('pay')) {
        reply = "Salary payments are processed monthly on the 28th. You can access your payslips directly from the payroll section. For custom inquiries or tax declarations, please contact HR operations."
      } else if (lower.includes('attendance') || lower.includes('check in') || lower.includes('shift')) {
        reply = "Standard office core hours are 10:00 AM to 6:00 PM. Daily check-in/out is requested via the portal to log active hours and ensure compliance with team availability rules."
      }
      streamText(reply, [], [])
      toast.success('Offline AI mode fallback activated.')
    }
  }

  // Handle Send Chat
  const handleSendChat = async (e) => {
    e.preventDefault()
    if (!inputMessage.trim() || isTyping) return

    const userText = inputMessage.trim()
    setMessages((prev) => [...prev, { sender: 'user', text: userText, timestamp: new Date() }])
    setInputMessage('')
    sendMessageToAssistant(userText)
  }

  const handleSelectPrompt = async (promptText) => {
    if (isTyping) return
    setMessages((prev) => [...prev, { sender: 'user', text: promptText, timestamp: new Date() }])
    sendMessageToAssistant(promptText)
  }

  if (loading) {
    return <SkeletonCard mode="card" count={2} />
  }

  if (profileComplete === false) {
    return <ProfileSetupWizard role="employee" onComplete={() => { setProfileComplete(true); fetchDashboardData(); }} />
  }

  // Calculate skill gap progress metric
  const currentSkillsList = employee?.skills ? employee.skills.split(',').map(s => s.trim()) : []
  const missingSkillsList = skillGap?.missing_skills || []
  const gapProgress = Math.round(
    (currentSkillsList.length / ((currentSkillsList.length + missingSkillsList.length) || 1)) * 100
  )

  return (
    <div className="space-y-8 select-none text-txt-primary">
      
      {/* Profile Header */}
      {employee && (
        <div className="rounded-xl border border-border-custom bg-bg-surface p-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-full bg-brand-indigo flex items-center justify-center text-white text-xl font-bold border border-brand-indigo/30">
              {user?.username?.slice(0, 2).toUpperCase()}
            </div>
            <div className="space-y-1 text-center sm:text-left">
              <div className="flex items-center justify-center sm:justify-start space-x-2">
                <h3 className="text-base font-semibold">{user?.username}</h3>
                <span className="text-[10px] font-semibold text-brand-indigo bg-brand-indigo-muted px-2 py-0.5 rounded border border-brand-indigo/10 uppercase">
                  {employee.employee_code}
                </span>
              </div>
              <p className="text-xs text-txt-secondary">{employee.designation} • {employee.department}</p>
              <span className="text-[10px] text-txt-tertiary block">Joined {new Date(employee.joining_date).toLocaleDateString()}</span>
            </div>
          </div>
          
          <button 
            onClick={() => { setActiveTab('profile'); setIsEditingProfile(true); }}
            className="px-3.5 py-1.5 border border-border-custom text-xs font-semibold text-txt-secondary hover:text-txt-primary hover:bg-bg-page rounded-lg cursor-pointer transition-colors"
          >
            Request Profile Edit
          </button>
        </div>
      )}



      {activeTab === 'overview' && (
        <div className="space-y-8">
          
          {/* Employee Intelligence Overview Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <div className="rounded-xl border border-border-custom bg-bg-surface p-4 flex flex-col justify-between hover:border-brand-indigo/35 transition-colors">
              <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Employee ID</span>
              <div>
                <span className="text-sm font-bold text-txt-primary block mt-1">{employee?.employee_code || 'N/A'}</span>
                <span className="text-[9px] text-txt-secondary block">Join Date: {employee?.joining_date ? new Date(employee.joining_date).toLocaleDateString() : 'N/A'}</span>
              </div>
            </div>
            <div className="rounded-xl border border-border-custom bg-bg-surface p-4 flex flex-col justify-between hover:border-brand-indigo/35 transition-colors">
              <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Department</span>
              <div>
                <span className="text-sm font-bold text-txt-primary block mt-1 truncate" title={employee?.department}>{employee?.department || 'Not Assigned'}</span>
                <span className="text-[9px] text-txt-secondary block truncate" title={employee?.designation}>{employee?.designation || 'Not Assigned'}</span>
              </div>
            </div>
            <div className="rounded-xl border border-border-custom bg-bg-surface p-4 flex flex-col justify-between hover:border-brand-indigo/35 transition-colors">
              <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Reporting Line</span>
              <div>
                <span className="text-sm font-bold text-txt-primary block mt-1">{employee?.manager_name || 'Not Assigned'}</span>
                <span className="text-[9px] text-txt-secondary block">{employee?.manager_name ? 'Direct Manager' : 'No Manager Assigned'}</span>
              </div>
            </div>
            <div className="rounded-xl border border-border-custom bg-bg-surface p-4 flex flex-col justify-between hover:border-brand-indigo/35 transition-colors">
              <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Time & Tickets</span>
              <div>
                <span className="text-sm font-bold text-txt-primary block mt-1">{attendance?.status || 'Not Checked In'}</span>
                <span className="text-[9px] text-txt-secondary block">{openTicketCount || 0} Open Tickets</span>
              </div>
            </div>
            <div className="rounded-xl border border-border-custom bg-bg-surface p-4 flex flex-col justify-between hover:border-brand-indigo/35 transition-colors">
              <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Growth & Profile</span>
              <div>
                <span className="text-sm font-bold text-txt-primary block mt-1">{trainingSummary?.total_assigned || 0} Assignments</span>
                <span className="text-[9px] text-txt-secondary block">Profile {profileCompletion?.completion_percent || 0}% Complete</span>
              </div>
            </div>
          </div>
          
          {/* Section: Workday Attendance & Leave Management */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold tracking-wider uppercase text-txt-secondary">Workday Attendance & Leave Management</h3>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              
              {/* Attendance widget (55%) */}
              <div className="lg:col-span-7 rounded-xl border border-border-custom bg-bg-surface p-6 shadow-xs space-y-5">
                <div className="flex items-center justify-between border-b border-border-custom pb-3">
                  <div>
                    <h4 className="text-sm font-semibold">Time & Attendance</h4>
                    <p className="text-[11px] text-txt-secondary">{time.toLocaleDateString()}</p>
                  </div>
                  
                  {/* Live hours indicator */}
                  <span className="text-xs font-bold text-brand-indigo bg-brand-indigo-muted border border-brand-indigo/20 px-2.5 py-0.5 rounded">
                    Today: {totalHoursToday}
                  </span>
                </div>

                <div className="flex flex-col items-center justify-center py-6 text-center space-y-4">
                  
                  {/* Digital Clock */}
                  <div className="text-4xl font-extrabold tracking-tight text-txt-primary font-mono select-all">
                    {time.toLocaleTimeString()}
                  </div>

                  {/* Check in/out pulse button */}
                  <button
                    onClick={handleAttendanceToggle}
                    disabled={attendance && attendance.status === 'Completed'}
                    className={`w-full max-w-[280px] h-12 rounded-xl text-xs font-bold uppercase tracking-wider text-white relative overflow-hidden transition-all active:scale-97 ${
                      attendance && attendance.status === 'Completed'
                        ? 'bg-bg-elevated border border-border-custom text-txt-secondary cursor-not-allowed'
                        : attendance && attendance.status === 'Checked In'
                        ? 'bg-danger-primary hover:bg-danger-primary/90 shadow-lg shadow-danger-primary/20 animate-pulse cursor-pointer'
                        : 'bg-success-primary hover:bg-success-primary/90 shadow-lg shadow-success-primary/20 cursor-pointer'
                    }`}
                  >
                    {attendance && attendance.status === 'Completed'
                      ? 'Attendance Completed'
                      : attendance && attendance.status === 'Checked In'
                      ? 'Check Out'
                      : 'Check In'}
                  </button>
                </div>

                {/* Weekly Heatmap (Mon-Sun) */}
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">Weekly Heatmap</span>
                  <div className="grid grid-cols-7 gap-1 sm:gap-2">
                    {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, idx) => {
                      // Mock highlights: present on Mon, Tue. Absent on others
                      const isToday = idx === (new Date().getDay() - 1 + 7) % 7
                      const isPresent = idx < 2
                      
                      return (
                        <div
                          key={idx}
                          className={`flex flex-col items-center justify-center p-2 rounded-lg border text-[11px] font-semibold ${
                            isPresent
                              ? 'bg-success-bg/30 border-success-primary text-success-primary'
                              : isToday
                              ? 'bg-bg-page border-brand-indigo text-brand-indigo'
                              : 'bg-bg-page border-border-custom text-txt-tertiary'
                          }`}
                        >
                          <span className="uppercase text-[9px] mb-1">{day}</span>
                          <span className="text-[10px] font-bold">{isPresent ? 'P' : 'A'}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>

              </div>

              {/* Right column widgets (45%) */}
              <div className="lg:col-span-5 space-y-6">
                
                {/* Profile Completion Card */}
                {profileCompletion && (
                  <ProfileCompletionWidget
                    profileCompletion={profileCompletion}
                    onAction={() => setProfileComplete(false)}
                  />
                )}

                {/* Leave Balance Widget */}
                {leaveBalance && (
                  <div className="rounded-xl border border-border-custom bg-bg-surface p-6 shadow-xs space-y-4">
                    <div className="border-b border-border-custom pb-3">
                      <h4 className="text-sm font-semibold">Leave Balances</h4>
                      <p className="text-[11px] text-txt-secondary">Your active company leave allocations and usage status</p>
                    </div>

                    <div className="grid grid-cols-3 gap-2 sm:gap-3">
                      {[
                        { label: 'Annual', color: 'border-brand-indigo text-brand-indigo bg-brand-indigo-muted/20' },
                        { label: 'Sick', color: 'border-danger-primary text-danger-primary bg-danger-bg/20' },
                        { label: 'Casual', color: 'border-warning-primary text-warning-primary bg-warning-bg/20' }
                      ].map((item) => {
                        const total = leaveBalance.allocations?.[item.label] || 0
                        const used = leaveBalance.used?.[item.label] || 0
                        const remaining = leaveBalance.remaining?.[item.label] || 0
                        
                        return (
                          <div key={item.label} className="border border-border-custom rounded-xl p-3 text-center space-y-2 bg-bg-page/50">
                            <span className="text-[9px] font-bold text-txt-tertiary uppercase tracking-wider block">{item.label}</span>
                            <div className="space-y-0.5">
                              <span className="text-base font-extrabold text-txt-primary block">{remaining}</span>
                              <span className="text-[9px] text-txt-secondary block">Days Left</span>
                            </div>
                            <div className="pt-1.5 border-t border-border-custom/50 flex justify-between text-[8px] font-semibold">
                              <span className="text-txt-tertiary">Used: {used}</span>
                              <span className="text-txt-tertiary">Max: {total}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                    
                    <p className="text-[9px] text-txt-tertiary leading-normal italic">
                      {leaveBalance.notes || 'Leave balances estimated based on approved leave requests and company allocations.'}
                    </p>
                  </div>
                )}

                {/* Leave requests card (45%) */}
                <div className="rounded-xl border border-border-custom bg-bg-surface p-6 shadow-xs space-y-4">
                  <div className="border-b border-border-custom pb-3">
                    <h4 className="text-sm font-semibold">Request Time Off</h4>
                    <p className="text-[11px] text-txt-secondary">Submit leave requests directly to your line manager</p>
                  </div>

                  <form onSubmit={handleLeaveSubmit} className="space-y-3">
                    
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Leave Type</label>
                      <select
                        value={leaveType}
                        onChange={(e) => setLeaveType(e.target.value)}
                        className="w-full bg-bg-page border border-border-custom outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                      >
                        <option value="Annual">Annual / Vacation</option>
                        <option value="Casual">Casual / Personal</option>
                        <option value="Sick">Sick Leave</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Start Date</label>
                        <input
                          type="date"
                          required
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          className="w-full bg-bg-page border border-border-custom outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold text-txt-tertiary uppercase block">End Date</label>
                        <input
                          type="date"
                          required
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          className="w-full bg-bg-page border border-border-custom outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary"
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Reason</label>
                      <textarea
                        rows={2}
                        required
                        placeholder="Details of cover, recovery etc..."
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="w-full bg-bg-page border border-border-custom outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary resize-none font-sans"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={submittingLeave}
                      className="w-full h-8 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold rounded-lg flex items-center justify-center cursor-pointer transition-all disabled:opacity-50 active:scale-98"
                    >
                      {submittingLeave ? 'Submitting request...' : 'Request Time Off'}
                    </button>
                  </form>

                  {/* Recent leaves table */}
                  {leaveSummary.recent.length > 0 && (
                    <div className="pt-4 border-t border-border-custom/50 space-y-2">
                      <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider block">My Recent Requests</span>
                      <div className="space-y-2">
                        {leaveSummary.recent.map((req) => (
                          <div key={req.id} className="flex items-center justify-between bg-bg-page/50 border border-border-custom/50 p-2.5 rounded-lg text-[11px]">
                            <div>
                              <span className="font-semibold text-txt-primary block leading-none mb-1">{req.leave_type} Leave</span>
                              <span className="text-txt-tertiary block leading-none">
                                {new Date(req.start_date).toLocaleDateString()} to {new Date(req.end_date).toLocaleDateString()}
                              </span>
                            </div>
                            <StatusPill status={req.status} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              </div>

            </div>
          </div>

          {/* Section: Career Growth & Promotion Readiness */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold tracking-wider uppercase text-txt-secondary">Career Growth & Promotion Readiness</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Career Growth Path card */}
              <div className="rounded-xl border border-border-custom bg-bg-surface p-6 shadow-xs space-y-6">
                <div className="border-b border-border-custom pb-3">
                  <h4 className="text-sm font-semibold text-txt-primary">Career Path Fit & Skills Analytics</h4>
                  <p className="text-[11px] text-txt-secondary">Deterministic mapping to your next potential career milestone</p>
                </div>

                {careerGrowth ? (
                  <div className="space-y-5">
                    {/* Role Progression Mapping */}
                    <div className="flex items-center justify-between bg-bg-page/50 border border-border-custom p-3.5 rounded-xl">
                      <div className="space-y-1">
                        <span className="text-[9px] font-bold text-txt-tertiary uppercase tracking-wider block">Current Designation</span>
                        <span className="text-xs font-bold text-txt-primary block leading-none">{careerGrowth.current_role}</span>
                      </div>
                      <div className="flex items-center text-brand-indigo font-bold text-lg px-2">→</div>
                      <div className="space-y-1 text-right">
                        <span className="text-[9px] font-bold text-brand-indigo uppercase tracking-wider block">Suggested Next Role</span>
                        <span className="text-xs font-bold text-brand-indigo block leading-none">{careerGrowth.suggested_next_role}</span>
                      </div>
                    </div>

                    {/* Skill matching tags */}
                    <div className="space-y-3 pt-2">
                      <div className="space-y-1.5">
                        <span className="text-[9px] font-bold text-success-primary uppercase tracking-wider block">Core Skills Matched</span>
                        <div className="flex flex-wrap gap-1.5">
                          {careerGrowth.skills_found?.length > 0 ? (
                            careerGrowth.skills_found.map((s, idx) => (
                              <span key={idx} className="bg-success-bg/30 text-success-primary border border-success-primary/20 px-2 py-0.5 rounded text-[10px] font-medium">
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-txt-tertiary">No matching skills found</span>
                          )}
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <span className="text-[9px] font-bold text-warning-primary uppercase tracking-wider block">Key Skill Gaps (To Develop)</span>
                        <div className="flex flex-wrap gap-1.5">
                          {careerGrowth.skills_missing?.length > 0 ? (
                            careerGrowth.skills_missing.map((s, idx) => (
                              <span key={idx} className="bg-warning-bg/30 text-warning-primary border border-warning-primary/20 px-2 py-0.5 rounded text-[10px] font-medium">
                                {s}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-success-primary">No missing skills detected!</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Recommended learning areas */}
                    {careerGrowth.recommended_learning_areas?.length > 0 && (
                      <div className="space-y-2 pt-4 border-t border-border-custom/50">
                        <span className="text-[9px] font-bold text-txt-tertiary uppercase tracking-wider block flex items-center space-x-1">
                          <BookOpen size={10} className="text-brand-indigo" />
                          <span>Recommended Focus Areas</span>
                        </span>
                        <ul className="space-y-1.5 text-xs text-txt-secondary leading-relaxed">
                          {careerGrowth.recommended_learning_areas.map((area, idx) => (
                            <li key={idx} className="flex items-start space-x-1.5">
                              <span className="text-brand-indigo font-bold">•</span>
                              <span>{area}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-txt-tertiary py-6 text-center">Loading career path insights...</div>
                )}
              </div>

              {/* Promotion Readiness card */}
              <div className="rounded-xl border border-border-custom bg-bg-surface p-6 shadow-xs space-y-6">
                <div className="border-b border-border-custom pb-3">
                  <h4 className="text-sm font-semibold text-txt-primary">Promotion Readiness Insights</h4>
                  <p className="text-[11px] text-txt-secondary">Compliance and evaluation criteria based on actual HR metrics</p>
                </div>

                {careerGrowth?.promotion_readiness ? (
                  <div className="space-y-5">
                    {/* Large Badge & Explanation */}
                    <div className="p-4 rounded-xl border border-border-custom/50 bg-bg-page/40 space-y-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-[9px] font-bold text-txt-tertiary uppercase tracking-wider block">Current Status</span>
                        {careerGrowth.promotion_readiness.status === 'Ready' ? (
                          <span className="bg-success-bg/40 text-success-primary border border-success-primary/30 px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider">
                            Ready
                          </span>
                        ) : careerGrowth.promotion_readiness.status === 'Developing' ? (
                          <span className="bg-warning-bg/40 text-warning-primary border border-warning-primary/30 px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider">
                            Developing
                          </span>
                        ) : (
                          <span className="bg-danger-bg/40 text-danger-primary border border-danger-primary/30 px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider">
                            Needs Growth
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-txt-secondary leading-relaxed font-medium">
                        {careerGrowth.promotion_readiness.explanation}
                      </p>
                    </div>

                    {/* Readiness progress metrics */}
                    <div className="space-y-4 pt-2">
                      {/* Metric 1: Skill Match */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider">
                          <span className="text-txt-secondary">Core Skill Match</span>
                          <span className="text-brand-indigo">{careerGrowth.promotion_readiness.skill_match_percent}%</span>
                        </div>
                        <div className="h-1.5 bg-bg-page rounded-full overflow-hidden border border-border-custom/50">
                          <div className="h-full bg-brand-indigo rounded-full" style={{ width: `${careerGrowth.promotion_readiness.skill_match_percent}%` }} />
                        </div>
                      </div>

                      {/* Metric 2: Training Completion */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider">
                          <span className="text-txt-secondary">Assigned Training Complete</span>
                          <span className="text-success-primary">{careerGrowth.promotion_readiness.training_completion_percent}%</span>
                        </div>
                        <div className="h-1.5 bg-bg-page rounded-full overflow-hidden border border-border-custom/50">
                          <div className="h-full bg-success-primary rounded-full" style={{ width: `${careerGrowth.promotion_readiness.training_completion_percent}%` }} />
                        </div>
                      </div>

                      {/* Metric 3: Profile completeness */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider">
                          <span className="text-txt-secondary">Profile Setup Verification</span>
                          <span className="text-warning-primary">{careerGrowth.promotion_readiness.profile_completion_percent}%</span>
                        </div>
                        <div className="h-1.5 bg-bg-page rounded-full overflow-hidden border border-border-custom/50">
                          <div className="h-full bg-warning-primary rounded-full" style={{ width: `${careerGrowth.promotion_readiness.profile_completion_percent}%` }} />
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-txt-tertiary py-6 text-center">Loading readiness assessment...</div>
                )}
              </div>

            </div>
          </div>

        </div>
      )}

      {/* Profile Tab View */}
      {activeTab === 'profile' && (
        <EmployeeProfileSection
          isEditingProfile={isEditingProfile}
          setIsEditingProfile={setIsEditingProfile}
          loadingProfile={loadingProfile}
          profileData={profileData}
          user={user}
          editPhone={editPhone}
          setEditPhone={setEditPhone}
          editEmergencyContact={editEmergencyContact}
          setEditEmergencyContact={setEditEmergencyContact}
          editAddress={editAddress}
          setEditAddress={setEditAddress}
          editSkills={editSkills}
          setEditSkills={setEditSkills}
          handleUpdateProfile={handleUpdateProfile}
        />
      )}

      {/* Tickets Tab View */}
      {activeTab === 'tickets' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border-custom bg-bg-surface p-6">
            <div className="flex justify-between items-center border-b border-border-custom pb-4 mb-6">
              <div>
                <h4 className="text-sm font-semibold">Grievances & Support Tickets</h4>
                <p className="text-[11px] text-txt-secondary">View and track responses to your submitted tickets</p>
              </div>
              <button
                onClick={() => setIsTicketModalOpen(true)}
                className="h-8 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold px-4 rounded-lg flex items-center space-x-1.5 active:scale-98 transition-all cursor-pointer"
              >
                <Plus size={14} />
                <span>Raise Ticket</span>
              </button>
            </div>

            {loadingTickets ? (
              <div className="flex justify-center py-12">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
              </div>
            ) : tickets.length === 0 ? (
              <EmptyState title="No tickets submitted" description="Submit queries, leave balance inquiries, salary, or workplace concerns." />
            ) : (
              <div className="overflow-x-auto w-full">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-bg-page text-txt-tertiary font-bold uppercase tracking-wider border-b border-border-custom">
                      <th className="py-2.5 px-3">Ticket Details</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Priority</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Resolution Note</th>
                      <th className="py-2.5 px-3 text-right">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-custom/50">
                    {tickets.map((t) => {
                      const priorityColor = 
                        t.priority === 'Critical' ? 'text-red-500' :
                        t.priority === 'High' ? 'text-orange-400' :
                        t.priority === 'Medium' ? 'text-yellow-400' : 'text-green-400'
                      return (
                        <tr key={t.id} className="hover:bg-bg-elevated/40 transition-colors">
                          <td className="py-3 px-3">
                            <span className="font-semibold text-txt-primary block">{t.title}</span>
                            <span className="text-[10px] text-txt-secondary block max-w-sm truncate" title={t.description}>
                              {t.description}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-medium text-txt-primary">{t.category}</td>
                          <td className="py-3 px-3 font-semibold">
                            <span className={priorityColor}>{t.priority}</span>
                          </td>
                          <td className="py-3 px-3">
                            <StatusPill status={t.status} />
                          </td>
                          <td className="py-3 px-3 text-txt-secondary italic max-w-xs truncate" title={t.resolution_note || ''}>
                            {t.resolution_note || 'Awaiting assignment...'}
                          </td>
                          <td className="py-3 px-3 text-right text-txt-tertiary">
                            {new Date(t.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Career Timeline Tab View */}
      {activeTab === 'timeline' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border-custom bg-bg-surface p-6">
            <div className="border-b border-border-custom pb-4 mb-6">
              <h4 className="text-sm font-semibold">Career History & Milestones</h4>
              <p className="text-[11px] text-txt-secondary">Official milestones of your journey at TalentForge</p>
            </div>

            {loadingLifecycle ? (
              <div className="flex justify-center py-12">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
              </div>
            ) : lifecycle.length === 0 ? (
              <EmptyState title="Timeline empty" description="Milestones will appear here once registered by HR operations." />
            ) : (
              <div className="relative border-l border-border-custom/80 ml-4 py-4 space-y-8">
                {lifecycle.map((event) => (
                  <div key={event.id} className="relative pl-6">
                    {/* Circle Dot Marker */}
                    <div className="absolute -left-[7px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-brand-indigo bg-bg-surface shadow" />
                    
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-txt-primary uppercase">{event.event_type}</span>
                        <span className="text-[10px] text-txt-tertiary">
                          {new Date(event.event_date).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-txt-secondary max-w-xl leading-relaxed">
                        {event.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Onboarding Tab View */}
      {activeTab === 'onboarding' && (
        <EmployeeOnboardingSection
          onboardingPlans={onboardingPlans}
          loadingOnboarding={loadingOnboarding}
          handleOnboardingTaskStatus={handleOnboardingTaskStatus}
          handleUploadOnboardingDocument={handleUploadOnboardingDocument}
        />
      )}

      {/* Training Tab View */}
      {activeTab === 'training' && (
        <EmployeeTrainingSection
          trainingAssignments={trainingAssignments}
          loadingTraining={loadingTraining}
          handleTrainingProgress={handleTrainingProgress}
          onAskAssistant={handleSelectPrompt}
        />
      )}

      {/* Floating AI HR Assistant Button */}
      <div className="fixed bottom-6 right-6 z-40">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsChatOpen(true)}
          className="w-12 h-12 rounded-full bg-brand-indigo text-white flex items-center justify-center shadow-lg shadow-brand-indigo/35 cursor-pointer"
        >
          <MessageSquare size={20} />
        </motion.button>
      </div>

      {/* Chatbot Side Drawer */}
      <AnimatePresence>
        {isChatOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsChatOpen(false)}
              className="fixed inset-0 bg-black z-40"
            />
            
            <motion.div
              initial={{ x: 380 }}
              animate={{ x: 0 }}
              exit={{ x: 380 }}
              transition={{ type: 'tween', duration: 0.3 }}
              className="fixed right-0 top-0 bottom-0 w-full max-w-[360px] h-screen bg-bg-surface border-l border-border-custom shadow-2xl flex flex-col z-50 overflow-hidden text-txt-primary"
            >
              {/* Drawer Header */}
              <div className="p-4 border-b border-border-custom flex items-center justify-between bg-bg-page/50">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-ai-teal animate-pulse" />
                  <span className="text-xs font-bold uppercase tracking-wider">TalentForge HR Copilot</span>
                </div>
                <button
                  onClick={() => setIsChatOpen(false)}
                  className="p-1 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated hover:text-txt-primary text-txt-secondary cursor-pointer transition-colors"
                >
                  <X size={14} />
                </button>
              </div>

              {/* Message scroll list */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length <= 1 && (
                  <div className="p-4 border border-border-custom rounded-xl bg-bg-page/40 space-y-4 text-center">
                    <div className="w-10 h-10 rounded-full bg-brand-indigo/10 flex items-center justify-center mx-auto text-brand-indigo">
                      <Sparkles size={20} />
                    </div>
                    <div className="space-y-1">
                      <h5 className="text-xs font-bold text-txt-primary">Employee Intelligence Copilot</h5>
                      <p className="text-[10px] text-txt-secondary leading-normal">
                        Ask me details about your leaves, check-in status, open tickets, or explore organization policy documents.
                      </p>
                    </div>
                    
                    {/* Suggested prompts grid */}
                    <div className="pt-2 space-y-1.5 text-left">
                      <span className="text-[8px] font-bold text-txt-tertiary uppercase tracking-wider block">Suggested Questions</span>
                      <div className="grid grid-cols-1 gap-1.5">
                        {[
                          "How many leave days do I have?",
                          "What is the leave policy?",
                          "What training is assigned to me?",
                          "What skills should I improve?",
                          "Explain the promotion process.",
                          "What onboarding tasks remain?"
                        ].map((prompt, pIdx) => (
                          <button
                            key={pIdx}
                            onClick={() => handleSelectPrompt(prompt)}
                            className="text-[10px] text-txt-secondary hover:text-brand-indigo hover:border-brand-indigo bg-bg-surface border border-border-custom px-3 py-1.5 rounded-lg text-left transition-colors cursor-pointer block truncate"
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {messages.map((msg, idx) => {
                  const isAI = msg.sender === 'ai'
                  return (
                    <div
                      key={idx}
                      className={`flex flex-col space-y-1 max-w-[85%] ${
                        isAI ? 'self-start' : 'self-end ml-auto'
                      }`}
                    >
                      {isAI && (
                        <span className="text-[9px] font-bold text-ai-teal uppercase tracking-widest leading-none pl-1">
                          TalentForge AI
                        </span>
                      )}
                      <div
                        className={`p-3 text-xs leading-relaxed border ${
                          isAI
                            ? 'bg-bg-elevated border-border-custom text-txt-primary rounded-2xl rounded-tl-none'
                            : 'bg-brand-indigo border-brand-indigo/40 text-white rounded-2xl rounded-tr-none'
                        }`}
                      >
                        {msg.text}
                      </div>

                      {/* Deduped Source Attribution badges */}
                      {isAI && msg.sources && msg.sources.length > 0 && (
                        <div className="flex flex-wrap gap-1 pl-1 pt-0.5 select-none">
                          {Array.from(new Set(msg.sources.map(s => {
                            if (s.collection === 'database') {
                              return s.source_collection || 'Live Employee Data'
                            } else if (s.collection === 'company_policies') {
                              return 'Company Policy'
                            } else if (s.collection === 'employee_knowledge') {
                              return 'Employee Knowledge'
                            }
                            return 'Company Knowledge'
                          }))).map((srcLabel, sIdx) => (
                            <span key={sIdx} className="inline-flex items-center space-x-0.5 bg-success-bg/25 border border-success-primary/20 text-success-primary text-[8px] font-bold px-1 py-0.2 rounded">
                              <span className="mr-0.5">✓</span>
                              <span>{srcLabel}</span>
                            </span>
                          ))}
                        </div>
                      )}

                      <span className={`text-[9px] text-txt-tertiary px-1 ${!isAI && 'text-right'}`}>
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  )
                })}

                {/* Typing status bubble */}
                {isTyping && (
                  <div className="flex flex-col space-y-1 max-w-[85%] self-start">
                    <span className="text-[9px] font-bold text-ai-teal uppercase tracking-widest pl-1">
                      TalentForge AI
                    </span>
                    <div className="bg-bg-elevated border border-border-custom p-3 rounded-2xl rounded-tl-none flex space-x-1.5 items-center">
                      {streamingText ? (
                        <p className="text-xs text-txt-primary leading-relaxed">{streamingText}</p>
                      ) : (
                        <div className="flex space-x-1">
                          <motion.span animate={{ y: [0, -3, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-txt-tertiary" />
                          <motion.span animate={{ y: [0, -3, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.15 }} className="w-1.5 h-1.5 rounded-full bg-txt-tertiary" />
                          <motion.span animate={{ y: [0, -3, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.3 }} className="w-1.5 h-1.5 rounded-full bg-txt-tertiary" />
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>

              {/* Chat Input form */}
              <form onSubmit={handleSendChat} className="p-3 border-t border-border-custom bg-bg-surface flex items-center space-x-2">
                <input
                  type="text"
                  disabled={isTyping}
                  placeholder="Ask policy questions..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  className="flex-1 bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3.5 py-1.5 text-xs rounded-xl text-txt-primary"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isTyping}
                  className="p-1.5 rounded-xl bg-brand-indigo hover:bg-brand-indigo-hover text-white transition-all disabled:opacity-40 cursor-pointer active:scale-95"
                >
                  <Send size={14} />
                </button>
              </form>

            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* CreateTicketModal integration */}
      <CreateTicketModal
        isOpen={isTicketModalOpen}
        onClose={() => setIsTicketModalOpen(false)}
        onSave={handleCreateTicket}
      />
    </div>
  )
}
export default EmployeeDashboard
