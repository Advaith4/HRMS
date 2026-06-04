import React, { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
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
  HelpCircle,
  FolderKanban,
  Award,
  LifeBuoy,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Settings,
  Lock,
  BookOpen,
  Target,
  Star,
  Brain,
  Milestone,
  UserCheck,
  Building2,
  DollarSign,
  ClipboardList,
} from 'lucide-react'

// ─── HR grouped nav definition ───────────────────────────────────────────────
const HR_NAV = [
  {
    type: 'item',
    path: '/dashboard/hr',
    label: 'Dashboard',
    icon: LayoutDashboard,
  },
  {
    type: 'group',
    id: 'recruitment',
    label: 'Recruitment',
    icon: Briefcase,
    children: [
      { path: '/hr/jobs',        label: 'Jobs',            icon: Briefcase  },
      { path: '/hr/candidates',  label: 'Candidates',      icon: Users      },
      { path: '/hr/pipeline',       label: 'Hiring Pipeline',  icon: GitMerge   },
      { path: '/hr/intelligence',   label: 'Interview Intel',  icon: Brain      },
    ],
  },
  {
    type: 'group',
    id: 'workforce',
    label: 'Workforce',
    icon: Building2,
    children: [
      { path: '/hr/directory',    label: 'Employee Directory', icon: Users       },
      { path: '/hr/departments',  label: 'Departments',        icon: FolderKanban },
      { path: '/hr/designations', label: 'Designations',       icon: Award       },
    ],
  },
  {
    type: 'group',
    id: 'operations',
    label: 'HR Operations',
    icon: ClipboardList,
    children: [
      { path: '/hr/leaves',     label: 'Leave Management', icon: CalendarCheck },
      { path: '/hr/tickets',    label: 'Tickets',          icon: LifeBuoy      },
      { path: '/hr/promotions', label: 'Promotions',       icon: TrendingUp    },
    ],
  },
  {
    type: 'group',
    id: 'talent',
    label: 'Talent Management',
    icon: Star,
    badge: 'Phase 2',
    children: [
      { path: '/hr/onboarding',       label: 'Onboarding',          icon: UserCheck },
      { path: '/hr/training',         label: 'Training',            icon: BookOpen },
      { path: '/hr/documents',        label: 'Documents',           icon: FileText },
      { label: 'Goals',               icon: Target,      locked: true, badge: 'Soon' },
      { label: 'Performance Reviews', icon: BarChart3,   locked: true, badge: 'Soon' },
      { label: 'Career Development',  icon: Milestone,   locked: true, badge: 'Soon' },
    ],
  },
  {
    type: 'item',
    path: '/dashboard/hr',
    label: 'Analytics',
    icon: BarChart3,
    locked: true,
    badge: 'Soon',
  },
  {
    type: 'item',
    path: '/dashboard/hr',
    label: 'Settings',
    icon: Settings,
    locked: true,
    badge: 'Soon',
  },
]

// ─── Manager nav ─────────────────────────────────────────────────────────────
const MANAGER_NAV = [
  {
    type: 'item',
    path: '/dashboard/manager',
    label: 'Dashboard',
    icon: LayoutDashboard,
  },
  {
    type: 'group',
    id: 'mgr-recruitment',
    label: 'Recruitment',
    icon: Briefcase,
    children: [
      { path: '/hr/pipeline',      label: 'Hiring Pipeline',  icon: GitMerge },
      { path: '/hr/candidates',    label: 'Candidates',       icon: Users    },
      { path: '/hr/intelligence',  label: 'Interview Intel',  icon: Brain    },
    ],
  },
  {
    type: 'item',
    path: '/manager/leaves',
    label: 'Leave Approvals',
    icon: CalendarCheck,
  },
  {
    type: 'item',
    path: '/manager/training',
    label: 'Team Training',
    icon: BookOpen,
  },
]

// ─── Employee nav ─────────────────────────────────────────────────────────────
const EMPLOYEE_NAV = [
  {
    type: 'item',
    path: '/dashboard/employee',
    label: 'Employee Portal',
    icon: UserCircle,
  },
]

// ─── Candidate nav ────────────────────────────────────────────────────────────
const CANDIDATE_NAV = [
  { type: 'item', path: '/dashboard/candidate', label: 'Home',            icon: Home     },
  { type: 'item', path: '/jobs',                label: 'Browse Jobs',     icon: Search   },
  { type: 'item', path: '/applications',        label: 'My Applications', icon: FileText },
]

// ─── Helper: does any child in a group match the current path? ────────────────
const groupIsActive = (group, pathname) =>
  group.children?.some(c => c.path && pathname === c.path)

// ─── Single flat link ─────────────────────────────────────────────────────────
const NavItem = ({ item, pathname }) => {
  const Icon = item.icon || HelpCircle
  const isActive = pathname === item.path

  if (item.locked) {
    return (
      <div className="flex items-center space-x-2.5 px-3 py-2 rounded-lg opacity-40 cursor-not-allowed select-none">
        <Icon size={15} className="text-txt-tertiary shrink-0" />
        <span className="text-xs font-medium text-txt-tertiary flex-1 truncate">{item.label}</span>
        {item.badge && (
          <span className="text-[9px] font-bold uppercase tracking-wider text-txt-tertiary bg-bg-page border border-border-custom px-1.5 py-0.5 rounded-full">
            {item.badge}
          </span>
        )}
        <Lock size={11} className="text-txt-tertiary shrink-0" />
      </div>
    )
  }

  return (
    <Link
      to={item.path}
      className={`group flex items-center space-x-2.5 px-3 py-2 rounded-lg transition-all duration-150 ${
        isActive
          ? 'bg-brand-indigo text-white shadow-sm'
          : 'text-txt-secondary hover:bg-bg-page hover:text-txt-primary'
      }`}
    >
      <Icon size={15} className="shrink-0" />
      <span className="text-xs font-medium flex-1 truncate">{item.label}</span>
      {item.badge && !isActive && (
        <span className="text-[9px] font-bold uppercase tracking-wider text-brand-indigo bg-brand-indigo-muted border border-brand-indigo/20 px-1.5 py-0.5 rounded-full">
          {item.badge}
        </span>
      )}
    </Link>
  )
}

// ─── Collapsible group ────────────────────────────────────────────────────────
const NavGroup = ({ group, pathname }) => {
  const hasActive = groupIsActive(group, pathname)
  const [open, setOpen] = useState(hasActive)

  // Auto-open the group when the route changes into it
  useEffect(() => {
    if (hasActive) setOpen(true)
  }, [pathname, hasActive])

  const GroupIcon = group.icon || HelpCircle

  return (
    <div>
      <button
        onClick={() => !group.locked && setOpen(o => !o)}
        className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg transition-all duration-150 select-none ${
          group.locked
            ? 'opacity-40 cursor-not-allowed'
            : hasActive
            ? 'text-brand-indigo bg-brand-indigo-muted/40'
            : 'text-txt-secondary hover:bg-bg-page hover:text-txt-primary'
        }`}
      >
        <GroupIcon size={15} className="shrink-0" />
        <span className="text-xs font-semibold flex-1 text-left truncate">{group.label}</span>
        {group.badge && (
          <span className="text-[9px] font-bold uppercase tracking-wider text-txt-tertiary bg-bg-page border border-border-custom px-1.5 py-0.5 rounded-full">
            {group.badge}
          </span>
        )}
        {group.locked ? (
          <Lock size={11} className="text-txt-tertiary shrink-0" />
        ) : open ? (
          <ChevronDown size={13} className="shrink-0 transition-transform" />
        ) : (
          <ChevronRight size={13} className="shrink-0 transition-transform" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {open && !group.locked && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="ml-4 mt-0.5 pl-3 border-l border-border-custom space-y-0.5 pb-1">
              {group.children.map((child, i) => {
                const ChildIcon = child.icon || HelpCircle
                const isActive = pathname === child.path

                if (child.locked) {
                  return (
                    <div key={i} className="flex items-center space-x-2 px-2.5 py-1.5 rounded-md opacity-35 cursor-not-allowed">
                      <ChildIcon size={13} className="text-txt-tertiary shrink-0" />
                      <span className="text-[11px] font-medium text-txt-tertiary flex-1">{child.label}</span>
                      {child.badge && (
                        <span className="text-[8px] font-bold uppercase tracking-wider text-txt-tertiary border border-border-custom px-1.5 py-0.5 rounded-full">
                          {child.badge}
                        </span>
                      )}
                    </div>
                  )
                }

                return (
                  <Link
                    key={child.path}
                    to={child.path}
                    className={`flex items-center space-x-2 px-2.5 py-1.5 rounded-md transition-all duration-150 ${
                      isActive
                        ? 'text-brand-indigo font-semibold bg-brand-indigo-muted/50'
                        : 'text-txt-secondary hover:text-txt-primary hover:bg-bg-page'
                    }`}
                  >
                    <ChildIcon size={13} className="shrink-0" />
                    <span className="text-[11px] font-medium">{child.label}</span>
                    {isActive && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-indigo shrink-0" />
                    )}
                  </Link>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Locked group — show collapsed children grayed out */}
        {open && group.locked && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="ml-4 mt-0.5 pl-3 border-l border-border-custom/40 space-y-0.5 pb-1 opacity-35">
              {group.children.map((child, i) => {
                const ChildIcon = child.icon || HelpCircle
                return (
                  <div key={i} className="flex items-center space-x-2 px-2.5 py-1.5 rounded-md cursor-not-allowed">
                    <ChildIcon size={13} className="text-txt-tertiary shrink-0" />
                    <span className="text-[11px] text-txt-tertiary">{child.label}</span>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Section divider ──────────────────────────────────────────────────────────
const SectionDivider = ({ label }) => (
  <div className="px-3 pt-4 pb-1">
    <span className="text-[9px] font-bold uppercase tracking-widest text-txt-tertiary">{label}</span>
  </div>
)

// ─── Main sidebar ─────────────────────────────────────────────────────────────
export const Sidebar = () => {
  const { role, user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()
  const pathname = location.pathname

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const getInitials = () => {
    if (!user?.username) return 'TF'
    return user.username.slice(0, 2).toUpperCase()
  }

  const getNav = () => {
    if (role === 'hr' || role === 'admin') return HR_NAV
    if (role === 'manager') return MANAGER_NAV
    if (role === 'employee') return EMPLOYEE_NAV
    return CANDIDATE_NAV
  }

  const nav = getNav()

  // Flat links for mobile bottom bar (top-level items and first child of each group)
  const mobileLinks = nav.flatMap(item => {
    if (item.type === 'item' && !item.locked) return [item]
    if (item.type === 'group' && !item.locked && item.children?.[0]?.path) return [item.children[0]]
    return []
  }).slice(0, 5) // max 5 on mobile

  return (
    <>
      {/* ── Desktop Sidebar ─────────────────────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-56 shrink-0 h-screen sticky top-0 left-0 bg-white border-r border-border-custom select-none z-30 overflow-hidden">

        {/* Logo strip */}
        <div className="flex items-center space-x-2.5 px-4 py-4 border-b border-border-custom shrink-0">
          <Link to="/" className="w-8 h-8 rounded-lg bg-brand-indigo flex items-center justify-center text-white font-extrabold text-sm shadow-sm hover:scale-105 transition-all">
            TF
          </Link>
          <div className="flex flex-col leading-none">
            <span className="text-xs font-bold text-txt-primary tracking-tight">TalentForge</span>
            <span className="text-[10px] text-txt-tertiary font-medium mt-0.5">HRMS Platform</span>
          </div>
        </div>

        {/* Nav items — scrollable */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {nav.map((item, idx) => {
            if (item.type === 'item') {
              return <NavItem key={item.path + idx} item={item} pathname={pathname} />
            }
            if (item.type === 'group') {
              return <NavGroup key={item.id} group={item} pathname={pathname} />
            }
            return null
          })}
        </nav>

        {/* Bottom user strip */}
        <div className="border-t border-border-custom px-3 py-3 shrink-0 space-y-1">
          <div className="flex items-center space-x-2.5 px-2 py-1.5 rounded-lg">
            <div className="w-7 h-7 rounded-full bg-brand-indigo text-white font-bold text-xs flex items-center justify-center shrink-0">
              {getInitials()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-txt-primary truncate">{user?.username || 'User'}</p>
              <p className="text-[10px] text-txt-tertiary capitalize">{role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-txt-secondary hover:text-danger-primary hover:bg-danger-bg/20 transition-all cursor-pointer text-xs font-medium"
          >
            <LogOut size={14} className="shrink-0" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ── Mobile Bottom Bar ───────────────────────────────────────────── */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 h-14 bg-white border-t border-border-custom flex items-center justify-around px-2 z-30">
        {mobileLinks.map((link, i) => {
          const Icon = link.icon || HelpCircle
          const isActive = pathname === link.path
          return (
            <Link
              key={link.path + i}
              to={link.path}
              className={`flex flex-col items-center justify-center px-3 py-1.5 rounded-lg transition-colors ${
                isActive ? 'text-brand-indigo' : 'text-txt-tertiary'
              }`}
            >
              <Icon size={18} />
              <span className="text-[9px] mt-0.5 font-semibold truncate max-w-[48px] text-center">{link.label}</span>
            </Link>
          )
        })}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center justify-center px-3 py-1.5 rounded-lg text-txt-tertiary hover:text-danger-primary transition-colors"
        >
          <LogOut size={18} />
          <span className="text-[9px] mt-0.5 font-semibold">Out</span>
        </button>
      </div>
    </>
  )
}

export default Sidebar
