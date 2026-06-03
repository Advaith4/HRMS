import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import {
  LayoutDashboard,
  Briefcase,
  GitMerge,
  Users,
  CalendarCheck,
  UserCircle,
  Home,
  Search,
  FileText,
  LogOut,
  HelpCircle
} from 'lucide-react'

const IconMap = {
  LayoutDashboard,
  Briefcase,
  GitMerge,
  Users,
  CalendarCheck,
  UserCircle,
  Home,
  Search,
  FileText,
  LogOut,
  HelpCircle
}

export const Sidebar = () => {
  const { role, user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Get user initials
  const getInitials = () => {
    if (!user || !user.username) return 'TF'
    return user.username.slice(0, 2).toUpperCase()
  }

  // Define nav links by role
  const getNavLinks = () => {
    if (role === 'hr' || role === 'admin') {
      return [
        { path: '/dashboard/hr', label: 'HR Dashboard', icon: 'LayoutDashboard' },
        { path: '/hr/jobs', label: 'Manage Jobs', icon: 'Briefcase' },
        { path: '/hr/pipeline', label: 'Pipeline Board', icon: 'GitMerge' },
        { path: '/hr/candidates', label: 'Candidates Table', icon: 'Users' },
        { path: '/hr/leaves', label: 'Leave Approvals', icon: 'CalendarCheck' },
      ]
    }
    if (role === 'manager') {
      return [
        { path: '/dashboard/manager', label: 'Manager Dashboard', icon: 'LayoutDashboard' },
        { path: '/hr/pipeline', label: 'Pipeline View', icon: 'GitMerge' },
        { path: '/hr/candidates', label: 'Candidates List', icon: 'Users' },
        { path: '/manager/leaves', label: 'Leave Approvals', icon: 'CalendarCheck' },
      ]
    }
    if (role === 'employee') {
      return [
        { path: '/dashboard/employee', label: 'Employee Portal', icon: 'UserCircle' },
      ]
    }
    // Candidate
    return [
      { path: '/dashboard/candidate', label: 'Home Feed', icon: 'Home' },
      { path: '/jobs', label: 'Search Jobs', icon: 'Search' },
      { path: '/applications', label: 'My Applications', icon: 'FileText' },
    ]
  }

  const links = getNavLinks()

  return (
    <>
      {/* Desktop Sidebar (hidden on mobile) */}
      <aside className="hidden md:flex flex-col items-center justify-between w-16 h-screen sticky top-0 left-0 bg-bg-page border-r border-border-custom py-6 select-none z-30">
        
        {/* Top Logo */}
        <div className="flex flex-col items-center">
          <Link to="/" className="w-10 h-10 rounded-lg bg-brand-indigo/10 border border-brand-indigo/20 flex items-center justify-center text-brand-indigo font-bold text-lg hover:scale-105 transition-all">
            TF
          </Link>
        </div>

        {/* Navigation Middle */}
        <nav className="flex-1 flex flex-col items-center justify-center space-y-4 my-8 w-full">
          {links.map((link) => {
            const Icon = IconMap[link.icon] || IconMap.HelpCircle
            const isActive = location.pathname === link.path
            
            return (
              <div key={link.path} className="relative group w-full flex justify-center">
                {/* Active left border indicator */}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-6 bg-brand-indigo" />
                )}
                
                <Link
                  to={link.path}
                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
                    isActive
                      ? 'text-brand-indigo bg-brand-indigo-muted/50 border border-brand-indigo/20'
                      : 'text-txt-tertiary hover:text-txt-secondary hover:bg-bg-surface'
                  }`}
                >
                  <Icon size={20} />
                </Link>

                {/* Styled Tooltip */}
                <div className="absolute left-16 top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block pointer-events-none bg-bg-elevated border border-border-hover-custom text-txt-primary text-xs font-semibold px-2.5 py-1.5 rounded shadow-xl whitespace-nowrap z-50">
                  {link.label}
                </div>
              </div>
            )
          })}
        </nav>

        {/* Bottom User Controls */}
        <div className="flex flex-col items-center space-y-4 w-full">
          <div className="relative group flex justify-center">
            <div className="w-8 h-8 rounded-full bg-brand-indigo text-white font-bold text-xs flex items-center justify-center border border-brand-indigo/30 cursor-pointer">
              {getInitials()}
            </div>
            <div className="absolute left-16 top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block pointer-events-none bg-bg-elevated border border-border-hover-custom text-txt-primary text-xs font-semibold px-2.5 py-1.5 rounded shadow-xl whitespace-nowrap z-50">
              {user?.username || 'User'} ({role})
            </div>
          </div>

          <div className="relative group w-full flex justify-center">
            <button
              onClick={handleLogout}
              className="w-10 h-10 rounded-lg flex items-center justify-center text-txt-tertiary hover:text-danger-primary hover:bg-danger-bg/20 transition-all cursor-pointer"
            >
              <LogOut size={20} />
            </button>
            <div className="absolute left-16 top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block pointer-events-none bg-bg-elevated border border-danger-primary/30 text-danger-primary text-xs font-semibold px-2.5 py-1.5 rounded shadow-xl whitespace-nowrap z-50">
              Sign Out
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Navigation Bar (fixed bottom, hidden on desktop) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 h-14 bg-bg-surface border-t border-border-custom flex items-center justify-around px-4 z-30">
        {links.map((link) => {
          const Icon = IconMap[link.icon] || IconMap.HelpCircle
          const isActive = location.pathname === link.path
          
          return (
            <Link
              key={link.path}
              to={link.path}
              className={`flex flex-col items-center justify-center p-2 rounded-lg transition-colors ${
                isActive ? 'text-brand-indigo' : 'text-txt-tertiary'
              }`}
            >
              <Icon size={20} />
            </Link>
          )
        })}
        {/* Logout button on mobile */}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center justify-center p-2 rounded-lg text-txt-tertiary hover:text-danger-primary"
        >
          <LogOut size={20} />
        </button>
      </div>
    </>
  )
}
export default Sidebar
