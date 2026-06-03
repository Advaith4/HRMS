import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { 
  X, Bell, CheckSquare, UserPlus, Calendar, AlertCircle, 
  TrendingUp, DollarSign, MessageSquare, ShieldCheck 
} from 'lucide-react'
import { listNotifications, markRead, markAllRead } from '../../api'
import toast from 'react-hot-toast'

export const NotificationDrawer = ({ isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      fetchNotifications()
    }
  }, [isOpen])

  const fetchNotifications = async () => {
    setLoading(true)
    try {
      const data = await listNotifications()
      setNotifications(data.notifications || [])
      setUnreadCount(data.unread_count || 0)
    } catch (err) {
      console.error('Failed to load notifications', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkRead = async (id) => {
    try {
      await markRead(id)
      fetchNotifications()
    } catch (err) {
      console.error(err)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await markAllRead()
      toast.success('All notifications marked as read')
      fetchNotifications()
    } catch (err) {
      toast.error('Failed to mark all read')
    }
  }

  const getNotifIcon = (type) => {
    if (type === 'lifecycle_event') return <UserPlus size={16} className="text-green-600" />
    if (type === 'leave_request') return <Calendar size={16} className="text-blue-600" />
    if (type === 'ticket_raised') return <AlertCircle size={16} className="text-red-600" />
    if (type === 'ticket_status_change') return <MessageSquare size={16} className="text-brand-indigo" />
    if (type === 'promotion') return <TrendingUp size={16} className="text-violet-600" />
    if (type === 'salary_revision') return <DollarSign size={16} className="text-amber-600" />
    return <Bell size={16} className="text-slate-400" />
  }

  const getRelativeTime = (isoString) => {
    try {
      const date = new Date(isoString)
      const now = new Date()
      const diffMs = now - date
      const diffMin = Math.floor(diffMs / (1000 * 60))
      const diffHr = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDay = Math.floor(diffMs / (1000 * 60 * 60 * 24))

      if (diffMin < 1) return 'Just now'
      if (diffMin < 60) return `${diffMin}m ago`
      if (diffHr < 24) return `${diffHr}h ago`
      return `${diffDay}d ago`
    } catch (e) {
      return ''
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Overlay backdrop */}
      <div onClick={onClose} className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" />

      {/* Drawer content */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="relative w-full max-w-sm h-full border-l border-slate-200 bg-white p-6 shadow-2xl flex flex-col justify-between"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
            <div className="flex items-center gap-2">
              <Bell className="text-brand-indigo" size={18} />
              <h3 className="text-lg font-semibold text-slate-900 tracking-tight">Notifications</h3>
              {unreadCount > 0 && (
                <span className="rounded-full bg-red-50 border border-red-100 px-2 py-0.5 text-xs font-bold text-red-600">
                  {unreadCount} New
                </span>
              )}
            </div>
            <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition">
              <X size={18} />
            </button>
          </div>

          {/* Mark All Read Option */}
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="flex items-center gap-1.5 text-xs text-brand-indigo hover:text-brand-indigo-hover font-semibold mb-4 transition text-left"
            >
              <CheckSquare size={14} />
              Mark all as read
            </button>
          )}

          {/* Notifications Scroll Area */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-3">
            {loading && notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 gap-2">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
                <span className="text-slate-500 text-xs font-medium">Syncing notifications...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <ShieldCheck className="text-slate-300 mb-4" size={48} />
                <h4 className="text-sm font-semibold text-slate-800 mb-1">All caught up!</h4>
                <p className="text-slate-500 text-xs max-w-[200px]">No new notifications or system updates at this time.</p>
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && handleMarkRead(n.id)}
                  className={`relative flex gap-3 rounded-xl border p-3.5 transition cursor-pointer ${
                    n.is_read
                      ? 'border-slate-100 bg-white hover:bg-slate-50'
                      : 'border-brand-indigo/20 bg-brand-indigo-muted/30 hover:bg-brand-indigo-muted/50 before:absolute before:left-0 before:top-3 before:bottom-3 before:w-0.5 before:bg-brand-indigo'
                  }`}
                >
                  <span className="rounded-lg bg-slate-50 border border-slate-100 p-2 h-9 w-9 flex items-center justify-center shadow-inner self-start">
                    {getNotifIcon(n.event_type)}
                  </span>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className={`text-xs font-bold text-slate-800 tracking-tight ${!n.is_read && 'text-brand-indigo'}`}>
                        {n.title}
                      </h4>
                      <span className="text-[10px] text-slate-400 whitespace-nowrap">
                        {getRelativeTime(n.created_at)}
                      </span>
                    </div>
                    <p className="text-slate-500 text-[11px] leading-relaxed">
                      {n.message}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-100 pt-4 mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 bg-transparent px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
          >
            Close Panel
          </button>
        </div>
      </motion.div>
    </div>
  )
}
