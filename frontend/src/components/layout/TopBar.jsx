import React, { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Bell, Sun, Moon } from 'lucide-react'
import { listNotifications } from '../../api'
import { NotificationDrawer } from '../drawers/NotificationDrawer'

export const TopBar = () => {
  const { role, user, isAuthenticated } = useAuthStore()
  const location = useLocation()
  const [unreadCount, setUnreadCount] = useState(0)
  const [isDarkMode, setIsDarkMode] = useState(true) // Dark by default in this premium design
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

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

          {/* Dark/Light mode toggle */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated hover:text-txt-primary text-txt-secondary transition-colors cursor-pointer"
          >
            {isDarkMode ? <Sun size={15} /> : <Moon size={15} />}
          </button>

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

          {/* User initials chip */}
          <div className="flex items-center space-x-2 border-l border-border-custom pl-4">
            <span className="text-xs font-semibold text-txt-secondary hidden sm:inline">
              {user?.username}
            </span>
          </div>
        </div>
      </header>

      {/* Notification Drawer */}
      <NotificationDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
    </>
  )
}
export default TopBar
