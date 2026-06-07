import React, { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Bell, ChevronDown, LogOut, UserCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { listNotifications } from '../../api'
import { NotificationDrawer } from '../drawers/NotificationDrawer'

export const TopBar = () => {
  const { role, user, isAuthenticated, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()
  const [unreadCount, setUnreadCount] = useState(0)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  const handleLogout = () => {
    setDropdownOpen(false)
    logout()
    navigate('/login')
  }

  const getInitials = () => {
    if (!user?.username) return 'TF'
    return user.username.slice(0, 2).toUpperCase()
  }

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])


  const fetchUnreadCount = async () => {
    if (!isAuthenticated) return
    try {
      const data = await listNotifications()
      setUnreadCount(data.unread_count || 0)
    } catch (err) {
      console.error('Failed to fetch unread notifications count:', err)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      fetchUnreadCount()
      const interval = setInterval(fetchUnreadCount, 60000)
      return () => clearInterval(interval)
    }
  }, [isAuthenticated])

  // Refetch when drawer closes (in case user marked notifications as read)
  useEffect(() => {
    if (!isDrawerOpen && isAuthenticated) {
      fetchUnreadCount()
    }
  }, [isDrawerOpen, isAuthenticated])

  // Compute breadcrumbs and titles
  const getPageContext = () => {
    const path = location.pathname
    if (path.startsWith('/dashboard/hr')) {
      return { title: 'Talent Acquisition', breadcrumb: 'HR Portal / Dashboard' }
    }
    if (path.startsWith('/dashboard/manager')) {
      return { title: 'Performance & Pipeline', breadcrumb: 'Manager Portal / Leaderboard' }
    }
    if (path.startsWith('/dashboard/employee')) {
      return { title: 'Employee Hub', breadcrumb: 'Employee Portal / Overview' }
    }
    if (path.startsWith('/dashboard/candidate')) {
      return { title: 'Candidate Portal', breadcrumb: 'Candidate Portal / Home' }
    }
    if (path.startsWith('/hr/copilot')) {
      return { title: 'HR Copilot', breadcrumb: 'Talent Intelligence / Copilot' }
    }
    if (path.startsWith('/career-assistant')) {
      return { title: 'Career Assistant', breadcrumb: 'Candidate Portal / Assistant' }
    }
    if (path.startsWith('/hr/jobs')) {
      return { title: 'Job Openings', breadcrumb: 'HR Portal / Job Management' }
    }
    if (path.startsWith('/hr/pipeline')) {
      return { title: 'Recruitment Funnel', breadcrumb: 'Talent Acquisition / Pipeline' }
    }
    if (path.startsWith('/hr/candidates')) {
      return { title: 'Talent Pool', breadcrumb: 'Talent Acquisition / Candidates' }
    }
    if (path.startsWith('/hr/directory')) {
      return { title: 'Employee Directory', breadcrumb: 'HR Portal / Employee Directory' }
    }
    if (path.startsWith('/hr/departments')) {
      return { title: 'Departments', breadcrumb: 'HR Portal / Departments' }
    }
    if (path.startsWith('/hr/designations')) {
      return { title: 'Designations', breadcrumb: 'HR Portal / Designations' }
    }
    if (path.startsWith('/hr/tickets')) {
      return { title: 'Grievances & Tickets', breadcrumb: 'HR Portal / Grievance Dashboard' }
    }
    if (path.startsWith('/hr/promotions')) {
      return { title: 'Promotions', breadcrumb: 'HR Portal / Promotion Dashboard' }
    }
    if (path.startsWith('/jobs')) {
      return { title: 'Explore Careers', breadcrumb: 'Careers / Jobs Feed' }
    }
    if (path.startsWith('/applications')) {
      return { title: 'My Job Applications', breadcrumb: 'Careers / Applications' }
    }
    return { title: 'TalentForge AI', breadcrumb: 'TalentForge AI' }
  }

  const { title, breadcrumb } = getPageContext()

  return (
    <>
      <header className="w-full h-14 border-b border-border-custom bg-bg-page flex items-center justify-between px-8 select-none z-20">
        
        {/* Title & Breadcrumbs */}
        <div className="flex flex-col">
          <h1 className="text-sm font-medium text-txt-primary m-0 leading-none">
            {title}
          </h1>
          <span className="text-[11px] text-txt-tertiary mt-1 leading-none">
            {breadcrumb}
          </span>
        </div>

        {/* Right Tools */}
        <div className="flex items-center space-x-4">
          
          {/* Role Badge Pill */}
          {role && (
            <span className="text-[11px] font-semibold text-brand-indigo bg-brand-indigo-muted border border-brand-indigo/20 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              {role}
            </span>
          )}

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated hover:text-txt-primary text-txt-secondary transition-colors cursor-pointer"
            >
              <Bell size={15} />
            </button>
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-danger-primary text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-bg-page">
                {unreadCount}
              </span>
            )}
          </div>

          {/* User initials chip / Dropdown */}
          <div className="relative border-l border-border-custom pl-4" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(o => !o)}
              className="flex items-center space-x-2 px-2 py-1.5 rounded-lg hover:bg-bg-elevated transition-colors cursor-pointer select-none"
            >
              {/* Avatar circle */}
              <div className="w-7 h-7 rounded-full bg-brand-indigo text-white font-bold text-xs flex items-center justify-center shrink-0">
                {getInitials()}
              </div>
              {/* Username */}
              <span className="text-xs font-semibold text-txt-secondary hidden sm:inline">
                {user?.username || 'User'}
              </span>
              {/* Chevron Down */}
              <ChevronDown size={14} className={`text-txt-tertiary transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            <AnimatePresence>
              {dropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-1.5 w-48 bg-white border border-border-custom rounded-xl shadow-lg p-1.5 z-50 flex flex-col space-y-0.5"
                >
                  {role === 'employee' && (
                    <button
                      onClick={() => {
                        setDropdownOpen(false)
                        navigate('/dashboard/employee?tab=profile')
                      }}
                      className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-txt-secondary hover:text-txt-primary hover:bg-bg-page transition-all cursor-pointer text-left text-xs font-medium"
                    >
                      <UserCircle size={14} className="shrink-0" />
                      <span>My Profile</span>
                    </button>
                  )}
                  
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-txt-secondary hover:text-danger-primary hover:bg-danger-bg/20 transition-all cursor-pointer text-left text-xs font-medium"
                  >
                    <LogOut size={14} className="shrink-0" />
                    <span>Sign Out</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </header>

      {/* Notification Drawer */}
      <NotificationDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
    </>
  )
}
export default TopBar
