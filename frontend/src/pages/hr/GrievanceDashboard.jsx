import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertCircle, ShieldAlert, User, Clock, 
  HelpCircle, DollarSign, Calendar, MessageSquare, ChevronDown, ChevronUp, UserCheck 
} from 'lucide-react'
import { listTickets, assignTicket, updateTicketStatus, listEmployees } from '../../api'
import { MetricCard } from '../../components/ui/MetricCard'
import { StatusPill } from '../../components/ui/StatusPill'
import toast from 'react-hot-toast'

export const GrievanceDashboard = () => {
  const [tickets, setTickets] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedTicketId, setExpandedTicketId] = useState(null)
  
  // Resolution note state per ticket
  const [resolutionNotes, setResolutionNotes] = useState({})
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('All')
  const [priorityFilter, setPriorityFilter] = useState('All')

  useEffect(() => {
    fetchTickets()
    fetchEmployees()
  }, [])

  const fetchTickets = async () => {
    setLoading(true)
    try {
      const data = await listTickets()
      setTickets(data || [])
    } catch (err) {
      toast.error('Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }

  const fetchEmployees = async () => {
    try {
      const data = await listEmployees()
      setEmployees(data || [])
    } catch (err) {
      console.error(err)
    }
  }

  const handleAssign = async (ticketId, assigneeUserId) => {
    if (!assigneeUserId) return
    try {
      await assignTicket(ticketId, parseInt(assigneeUserId))
      toast.success('Ticket assigned successfully')
      fetchTickets()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to assign ticket')
    }
  }

  const handleStatusChange = async (ticketId, newStatus) => {
    const note = resolutionNotes[ticketId] || ''
    try {
      await updateTicketStatus(ticketId, newStatus, note || undefined)
      toast.success(`Ticket set to ${newStatus}`)
      fetchTickets()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update ticket status')
    }
  }

  const handleResolutionNoteChange = (ticketId, value) => {
    setResolutionNotes((prev) => ({
      ...prev,
      [ticketId]: value
    }))
  }

  const getPriorityColor = (priority) => {
    if (priority === 'Critical') return 'bg-red-500/10 text-red-400 border-red-500/20'
    if (priority === 'High') return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
    if (priority === 'Medium') return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
    return 'bg-green-500/10 text-green-400 border-green-500/20'
  }

  const getCategoryIcon = (category) => {
    if (category === 'Leave Issue') return <Calendar size={14} className="text-blue-400" />
    if (category === 'Salary Issue') return <DollarSign size={14} className="text-green-400" />
    if (category === 'Manager Concern') return <ShieldAlert size={14} className="text-red-400" />
    if (category === 'Workplace Concern') return <MessageSquare size={14} className="text-purple-400" />
    return <HelpCircle size={14} className="text-zinc-400" />
  }

  // Filter logic
  const filteredTickets = tickets.filter((t) => {
    const matchesStatus = statusFilter === 'All' || t.status === statusFilter
    const matchesPriority = priorityFilter === 'All' || t.priority === priorityFilter
    return matchesStatus && matchesPriority
  })

  // Quick stats
  const openCount = tickets.filter((t) => t.status === 'Open').length
  const assignedCount = tickets.filter((t) => t.status === 'Assigned').length
  const reviewCount = tickets.filter((t) => t.status === 'In Review').length
  const resolvedCount = tickets.filter((t) => t.status === 'Resolved').length
  const criticalCount = tickets.filter((t) => t.priority === 'Critical' && t.status !== 'Closed').length

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Grievance & Tickets</h1>
        <p className="text-slate-500 text-sm">Review, assign, track and resolve grievance tickets raised by employees.</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard title="Open" value={openCount} icon={AlertCircle} description="Awaiting action" />
        <MetricCard title="Assigned" value={assignedCount} icon={User} description="Active review" />
        <MetricCard title="In Review" value={reviewCount} icon={Clock} description="Investigating" />
        <MetricCard title="Resolved" value={resolvedCount} icon={UserCheck} description="Completed tickets" />
        <MetricCard 
          title="Critical Issues" 
          value={criticalCount} 
          icon={ShieldAlert} 
          description="High severity unresolved"
          className={criticalCount > 0 ? 'border-red-300 bg-red-50 text-red-900' : ''}
        />
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-center bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex flex-wrap gap-4 items-center w-full">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-brand-indigo focus:outline-none transition cursor-pointer"
            >
              <option value="All">All Statuses</option>
              <option value="Open">Open</option>
              <option value="Assigned">Assigned</option>
              <option value="In Review">In Review</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-brand-indigo focus:outline-none transition cursor-pointer"
            >
              <option value="All">All Priorities</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Critical">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tickets Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
          <span className="text-slate-500 text-sm">Retrieving tickets...</span>
        </div>
      ) : filteredTickets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center border border-slate-200 rounded-2xl bg-white shadow-sm">
          <AlertCircle className="text-slate-400 mb-4" size={48} />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No tickets match</h3>
          <p className="text-slate-500 text-sm max-w-xs">There are currently no employee tickets matching the selected filters.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <AnimatePresence>
            {filteredTickets.map((t) => (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-brand-indigo transition"
              >
                <div className="flex flex-col lg:flex-row justify-between gap-4">
                  {/* Ticket Header & Metadata */}
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getPriorityColor(t.priority)}`}>
                        {t.priority}
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                        {getCategoryIcon(t.category)}
                        {t.category}
                      </span>
                      <StatusPill status={t.status} />
                    </div>

                    <h3 className="text-base font-semibold text-slate-900 tracking-tight">{t.title}</h3>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <User size={12} className="text-slate-400" />
                        Raised by: <span className="font-semibold text-slate-700">{t.employee_username}</span>
                      </span>
                      <span>•</span>
                      <span>
                        Date: {new Date(t.created_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>

                  {/* Assign & Actions Panel (HR Controls) */}
                  <div className="flex flex-wrap items-center gap-3 self-start lg:self-center">
                    {/* Assignment Selector */}
                    <div>
                      <select
                        value={t.assigned_to || ''}
                        onChange={(e) => handleAssign(t.id, e.target.value)}
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 focus:border-brand-indigo focus:outline-none transition cursor-pointer"
                      >
                        <option value="">Assign To...</option>
                        {employees.map((emp) => (
                          <option key={emp.user_id} value={emp.user_id}>
                            {emp.username} ({emp.department})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Status Changer */}
                    <div>
                      <select
                        value={t.status}
                        onChange={(e) => handleStatusChange(t.id, e.target.value)}
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 focus:border-brand-indigo focus:outline-none transition cursor-pointer"
                      >
                        <option value="Open">Set Open</option>
                        <option value="In Review">Set In Review</option>
                        <option value="Resolved">Set Resolved</option>
                        <option value="Closed">Set Closed</option>
                      </select>
                    </div>

                    {/* Expand/Collapse Toggle */}
                    <button
                      onClick={() => setExpandedTicketId(expandedTicketId === t.id ? null : t.id)}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition cursor-pointer"
                    >
                      {expandedTicketId === t.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>

                {/* Expanded Details Section */}
                <AnimatePresence>
                  {expandedTicketId === t.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden mt-4 border-t border-slate-100 pt-4 space-y-4 text-sm"
                    >
                      <div>
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Issue Description</h4>
                        <p className="text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100 whitespace-pre-wrap">
                          {t.description}
                        </p>
                      </div>

                      {/* Assignee display */}
                      {t.assigned_to_username && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <User size={12} className="text-brand-indigo" />
                          <span>Currently Assigned Resolver:</span>
                          <span className="font-semibold text-slate-700">{t.assigned_to_username}</span>
                        </div>
                      )}

                      {/* Resolution Note text area or print */}
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Resolution Note</h4>
                        {t.status === 'Closed' || t.status === 'Resolved' ? (
                          <div className="text-slate-700 bg-brand-indigo/5 border border-brand-indigo/15 p-4 rounded-xl">
                            {t.resolution_note || 'Resolved without remarks.'}
                          </div>
                        ) : (
                          <div className="flex gap-3">
                            <textarea
                              value={resolutionNotes[t.id] || ''}
                              onChange={(e) => handleResolutionNoteChange(t.id, e.target.value)}
                              placeholder="Enter resolution notes or status update remarks..."
                              rows="2"
                              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-slate-800 placeholder-slate-400 focus:border-brand-indigo focus:outline-none transition resize-none"
                            />
                            <button
                              onClick={() => handleStatusChange(t.id, 'Resolved')}
                              className="rounded-xl bg-brand-indigo px-4 py-2.5 text-xs font-semibold text-white hover:bg-brand-indigo-hover transition self-end whitespace-nowrap cursor-pointer"
                            >
                              Resolve Ticket
                            </button>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
