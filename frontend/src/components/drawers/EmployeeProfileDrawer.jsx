import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  X, User, Calendar, DollarSign, Award, Ticket, Edit, Save, 
  MapPin, Phone, Mail, FileText, Gift, Heart, UserMinus, UserCheck, Plus, TrendingUp 
} from 'lucide-react'
import { 
  getEmployeeProfile, updateEmployeeProfile, getLifecycle, 
  getSalaryHistory, addSalaryRevision, getPromotions, 
  addPromotion, listTickets, listDepartments, listDesignations, listEmployees 
} from '../../api'
import { useAuthStore } from '../../store/authStore'
import { StatusPill } from '../ui/StatusPill'
import { AddSalaryModal } from '../modals/AddSalaryModal'
import { AddPromotionModal } from '../modals/AddPromotionModal'
import toast from 'react-hot-toast'

export const EmployeeProfileDrawer = ({ isOpen, onClose, employeeId }) => {
  const { user } = useAuthStore()
  const isHR = user?.role === 'hr' || user?.role === 'admin'
  
  const [activeTab, setActiveTab] = useState('profile')
  const [loading, setLoading] = useState(false)
  const [empData, setEmpData] = useState(null)
  
  // Tab-specific data
  const [timeline, setTimeline] = useState([])
  const [salaryData, setSalaryData] = useState({ current_salary: 0, history: [] })
  const [promotionHistory, setPromotionHistory] = useState({ current_designation: '', history: [] })
  const [tickets, setTickets] = useState([])

  // Edit profile state
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState({})
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [employees, setEmployees] = useState([]) // For managers list

  // Modal control states
  const [isSalaryModalOpen, setIsSalaryModalOpen] = useState(false)
  const [isPromoModalOpen, setIsPromoModalOpen] = useState(false)

  useEffect(() => {
    if (isOpen && employeeId) {
      fetchProfile()
      fetchRelatedData()
      if (isHR) {
        loadDropdowns()
      }
    } else {
      setEditMode(false)
      setEmpData(null)
      setActiveTab('profile')
    }
  }, [isOpen, employeeId, activeTab])

  const fetchProfile = async () => {
    setLoading(true)
    try {
      const data = await getEmployeeProfile(employeeId)
      setEmpData(data)
      setFormData(data)
    } catch (err) {
      toast.error('Failed to retrieve employee profile')
    } finally {
      setLoading(false)
    }
  }

  const fetchRelatedData = async () => {
    if (!employeeId) return
    try {
      if (activeTab === 'timeline') {
        const events = await getLifecycle(employeeId)
        setTimeline(events || [])
      } else if (activeTab === 'salary') {
        const sal = await getSalaryHistory(employeeId)
        setSalaryData(sal || { current_salary: 0, history: [] })
      } else if (activeTab === 'promotions') {
        const promo = await getPromotions(employeeId)
        setPromotionHistory(promo || { current_designation: '', history: [] })
      } else if (activeTab === 'tickets') {
        const allT = await listTickets()
        // filter tickets of this employee
        setTickets(allT.filter((t) => t.employee_id === employeeId))
      }
    } catch (err) {
      console.error('Failed to load tab data', err)
    }
  }

  const loadDropdowns = async () => {
    try {
      const depts = await listDepartments()
      const desigs = await listDesignations()
      const emps = await listEmployees()
      setDepartments(depts.filter((d) => d.is_active))
      setDesignations(desigs.filter((dg) => dg.is_active))
      setEmployees(emps)
    } catch (err) {
      console.error(err)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    try {
      const payload = { ...formData }
      // format clean values
      if (payload.manager_id) payload.manager_id = parseInt(payload.manager_id)
      if (payload.department_id) payload.department_id = parseInt(payload.department_id)
      if (payload.designation_id) payload.designation_id = parseInt(payload.designation_id)
      if (payload.years_of_experience) payload.years_of_experience = parseFloat(payload.years_of_experience)
      
      await updateEmployeeProfile(employeeId, payload)
      toast.success('Profile updated successfully!')
      setEditMode(false)
      fetchProfile()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update profile')
    }
  }

  // Revision submit handlers
  const handleSalarySave = async (empId, payload) => {
    await addSalaryRevision(empId, payload)
    toast.success('Salary updated!')
    fetchRelatedData()
    fetchProfile()
  }

  const handlePromoSave = async (empId, payload) => {
    await addPromotion(empId, payload)
    toast.success('Promotion recorded!')
    fetchRelatedData()
    fetchProfile()
  }

  const getTimelineIcon = (type) => {
    if (type === 'Joined') return <UserCheck size={16} className="text-green-400" />
    if (type === 'Confirmed') return <Heart size={16} className="text-pink-400" />
    if (type === 'Promoted') return <TrendingUp size={16} className="text-yellow-400" />
    if (type === 'Exited') return <UserMinus size={16} className="text-red-400" />
    return <FileText size={16} className="text-indigo-400" />
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-40 overflow-hidden flex justify-end">
      {/* Overlay */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.6 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
      />

      {/* Slide-in Drawer Container */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="relative w-full max-w-xl h-full border-l border-slate-200 bg-white p-6 shadow-2xl flex flex-col justify-between"
      >
        <div>
          {/* Drawer Header */}
          <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-brand-indigo/10 flex items-center justify-center font-bold text-brand-indigo text-lg shadow-inner border border-brand-indigo/20">
                {empData ? (empData.full_name || empData.username)[0].toUpperCase() : '?'}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900 tracking-tight">
                  {empData ? empData.full_name || empData.username : 'Loading Profile...'}
                </h3>
                <p className="text-xs text-slate-500 font-mono">
                  Code: {empData?.employee_code || 'N/A'}
                </p>
              </div>
            </div>
            <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition">
              <X size={20} />
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 gap-4 mb-6 overflow-x-auto pb-1">
            {['profile', 'timeline', 'salary', 'promotions', 'tickets'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-2.5 text-xs font-semibold uppercase tracking-wider transition-colors relative ${
                  activeTab === tab ? 'text-brand-indigo font-bold' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {tab}
                {activeTab === tab && (
                  <motion.div layoutId="activeDrawerTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-indigo" />
                )}
              </button>
            ))}
          </div>

          {/* Tab Content Panel */}
          <div className="overflow-y-auto max-h-[calc(100vh-200px)] pr-2 space-y-4">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-2">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
                <span className="text-slate-500 text-xs font-medium">Fetching record...</span>
              </div>
            ) : !empData ? (
              <div className="text-zinc-500 text-sm py-10 text-center">Failed to load record details.</div>
            ) : activeTab === 'profile' ? (
              /* Profile Tab */
              <form onSubmit={handleSaveProfile} className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Employee Details</span>
                  {!editMode ? (
                    <button
                      type="button"
                      onClick={() => setEditMode(true)}
                      className="inline-flex items-center gap-1 text-xs text-brand-indigo hover:text-brand-indigo-hover font-semibold"
                    >
                      <Edit size={12} /> Edit Details
                    </button>
                  ) : (
                    <button
                      type="submit"
                      className="inline-flex items-center gap-1 text-xs text-green-600 hover:text-green-700 font-semibold"
                    >
                      <Save size={12} /> Save Changes
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Read-Only Details */}
                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Department</span>
                    {editMode && isHR ? (
                      <select
                        name="department_id"
                        value={formData.department_id || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      >
                        <option value="">Select Department</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.department || 'Not Set'}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Designation</span>
                    {editMode && isHR ? (
                      <select
                        name="designation_id"
                        value={formData.designation_id || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      >
                        <option value="">Select Designation</option>
                        {designations.map((dg) => (
                          <option key={dg.id} value={dg.id}>{dg.name}</option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.designation || 'Not Set'}</span>
                    )}
                  </div>

                  {/* Personal editable details */}
                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Full Name</span>
                    {editMode && isHR ? (
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.full_name || empData.username}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Email</span>
                    {editMode && isHR ? (
                      <input
                        type="email"
                        name="email"
                        value={formData.email || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.email || 'N/A'}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Phone</span>
                    {editMode ? (
                      <input
                        type="text"
                        name="phone"
                        value={formData.phone || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.phone || 'N/A'}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Emergency Contact</span>
                    {editMode ? (
                      <input
                        type="text"
                        name="emergency_contact"
                        value={formData.emergency_contact || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.emergency_contact || 'N/A'}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Status</span>
                    {editMode && isHR ? (
                      <select
                        name="status"
                        value={formData.status || 'Active'}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      >
                        <option value="Active">Active</option>
                        <option value="Probation">Probation</option>
                        <option value="On Leave">On Leave</option>
                        <option value="Resigned">Resigned</option>
                        <option value="Terminated">Terminated</option>
                      </select>
                    ) : (
                      <StatusPill status={empData.status || 'Active'} />
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Work Location</span>
                    {editMode && isHR ? (
                      <input
                        type="text"
                        name="work_location"
                        value={formData.work_location || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.work_location || 'N/A'}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Reporting Manager</span>
                    {editMode && isHR ? (
                      <select
                        name="manager_id"
                        value={formData.manager_id || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      >
                        <option value="">Select Manager</option>
                        {employees.map((e) => (
                          <option key={e.user_id} value={e.user_id}>{e.username}</option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.manager_name || 'None'}</span>
                    )}
                  </div>

                  <div className="rounded-xl bg-slate-50 p-3 border border-slate-200">
                    <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider">Years of Experience</span>
                    {editMode && isHR ? (
                      <input
                        type="number"
                        step="0.1"
                        name="years_of_experience"
                        value={formData.years_of_experience || ''}
                        onChange={handleInputChange}
                        className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">{empData.years_of_experience || '0'} years</span>
                    )}
                  </div>
                </div>

                <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                  <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider mb-1">Address</span>
                  {editMode ? (
                    <textarea
                      name="address"
                      value={formData.address || ''}
                      onChange={handleInputChange}
                      rows="2"
                      className="w-full bg-white border border-slate-200 rounded px-3 py-1.5 text-slate-800 text-xs mt-1 resize-none focus:border-brand-indigo focus:outline-none"
                    />
                  ) : (
                    <span className="text-sm text-slate-600">{empData.address || 'N/A'}</span>
                  )}
                </div>

                <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                  <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider mb-1">Certifications</span>
                  {editMode && isHR ? (
                    <textarea
                      name="certifications"
                      value={formData.certifications || ''}
                      onChange={handleInputChange}
                      rows="2"
                      className="w-full bg-white border border-slate-200 rounded px-3 py-1.5 text-slate-800 text-xs mt-1 resize-none focus:border-brand-indigo focus:outline-none"
                    />
                  ) : (
                    <span className="text-sm text-slate-600">{empData.certifications || 'None recorded.'}</span>
                  )}
                </div>

                <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                  <span className="block text-slate-400 text-[10px] uppercase font-bold tracking-wider mb-1">Skills</span>
                  {editMode ? (
                    <input
                      type="text"
                      name="skills"
                      value={formData.skills || ''}
                      onChange={handleInputChange}
                      placeholder="e.g. React, Node.js, Python"
                      className="w-full bg-white border border-slate-200 rounded px-3 py-1.5 text-slate-800 text-xs mt-1 focus:border-brand-indigo focus:outline-none"
                    />
                  ) : (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {empData.skills ? empData.skills.split(',').map((s, i) => (
                        <span key={i} className="rounded-lg bg-brand-indigo/10 px-2 py-1 text-xs text-brand-indigo font-semibold border border-brand-indigo/25">
                          {s.trim()}
                        </span>
                      )) : <span className="text-xs text-slate-400">No skills listed.</span>}
                    </div>
                  )}
                </div>
              </form>
            ) : activeTab === 'timeline' ? (
              /* Timeline Tab */
              <div className="relative border-l border-slate-200 ml-4 pl-6 space-y-6 py-2">
                {timeline.length === 0 ? (
                  <div className="text-slate-400 text-xs text-center py-6">No lifecycle events recorded.</div>
                ) : (
                  timeline.map((evt) => (
                    <div key={evt.id} className="relative">
                      {/* Timeline Dot Icon */}
                      <span className="absolute -left-[34px] top-0.5 rounded-full bg-white border border-slate-200 p-1.5 shadow">
                        {getTimelineIcon(evt.event_type)}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-slate-800">{evt.event_type}</span>
                          <span className="text-[10px] text-slate-400 font-mono">{evt.event_date}</span>
                        </div>
                        <p className="text-slate-600 text-xs mt-1 leading-relaxed">{evt.description}</p>
                        <span className="text-[10px] text-slate-400">Logged by: {evt.created_by_username}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : activeTab === 'salary' ? (
              /* Salary Tab */
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-xl bg-brand-indigo/5 p-4 border border-brand-indigo/15">
                  <div>
                    <span className="text-xs text-slate-500 block mb-0.5">Current Structured Salary</span>
                    <span className="text-xl font-bold text-brand-indigo flex items-center gap-0.5">
                      ₹{salaryData.current_salary ? salaryData.current_salary.toLocaleString('en-IN') : '0'} / yr
                    </span>
                  </div>
                  {isHR && (
                    <button
                      onClick={() => setIsSalaryModalOpen(true)}
                      className="rounded-lg bg-brand-indigo px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-indigo-hover transition flex items-center gap-1 cursor-pointer"
                    >
                      <Plus size={12} /> Add Revision
                    </button>
                  )}
                </div>

                <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
                  <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 font-semibold text-xs text-slate-500 uppercase tracking-wider">
                    Salary Increment History
                  </div>
                  {salaryData.history.length === 0 ? (
                    <div className="text-slate-400 text-xs py-10 text-center">No revision history found.</div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {salaryData.history.map((h) => (
                        <div key={h.id} className="p-4 space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-800">₹{h.new_salary.toLocaleString('en-IN')}</span>
                            <span className="text-slate-400">{h.effective_date}</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-500">
                            <span>Prev: ₹{h.previous_salary ? h.previous_salary.toLocaleString('en-IN') : '0'}</span>
                            {h.increment_percent && (
                              <span className="text-green-600 font-semibold">+{h.increment_percent}%</span>
                            )}
                          </div>
                          <div className="text-slate-400 mt-1 text-[11px] italic">Reason: {h.reason}</div>
                          <div className="text-[10px] text-slate-400">Approved by: {h.approved_by_username}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : activeTab === 'promotions' ? (
              /* Promotions Tab */
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-xl bg-brand-indigo/5 p-4 border border-brand-indigo/15">
                  <div>
                    <span className="text-xs text-slate-500 block mb-0.5">Current Designation</span>
                    <span className="text-base font-bold text-brand-indigo flex items-center gap-1">
                      <Award size={16} />
                      {promotionHistory.current_designation || empData.designation || 'Not Set'}
                    </span>
                  </div>
                  {isHR && (
                    <button
                      onClick={() => setIsPromoModalOpen(true)}
                      className="rounded-lg bg-brand-indigo px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-indigo-hover transition flex items-center gap-1 cursor-pointer"
                    >
                      <Plus size={12} /> Add Promotion
                    </button>
                  )}
                </div>

                <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
                  <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 font-semibold text-xs text-slate-500 uppercase tracking-wider">
                    Promotion & Progression Logs
                  </div>
                  {promotionHistory.history.length === 0 ? (
                    <div className="text-slate-400 text-xs py-10 text-center">No promotions recorded.</div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {promotionHistory.history.map((p) => (
                        <div key={p.id} className="p-4 space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-800">{p.new_designation}</span>
                            <span className="text-slate-400">{p.promotion_date}</span>
                          </div>
                          <div className="text-slate-500">Old Role: {p.old_designation}</div>
                          <div className="text-slate-400 mt-1 text-[11px] italic">Reason: {p.reason}</div>
                          <div className="text-[10px] text-slate-400">Approved by: {p.approved_by_username}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* Tickets Tab */
              <div className="space-y-4">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-slate-500">Grievances Raised ({tickets.length})</span>
                {tickets.length === 0 ? (
                  <div className="text-slate-400 text-xs py-10 text-center">No grievance tickets raised.</div>
                ) : (
                  <div className="space-y-3">
                    {tickets.map((t) => (
                      <div key={t.id} className="rounded-xl border border-slate-200 bg-white p-4 space-y-2 text-xs shadow-sm">
                        <div className="flex items-start justify-between gap-4">
                          <h4 className="font-semibold text-slate-800">{t.title}</h4>
                          <StatusPill status={t.status} />
                        </div>
                        <p className="text-slate-600 line-clamp-2">{t.description}</p>
                        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-100">
                          <span>Cat: {t.category} | Pri: {t.priority}</span>
                          <span>{new Date(t.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="border-t border-slate-200 pt-4 mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 bg-transparent px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition"
          >
            Close Drawer
          </button>
        </div>

        {/* Modals for revision (HR only) */}
        {isHR && (
          <>
            <AddSalaryModal
              isOpen={isSalaryModalOpen}
              onClose={() => setIsSalaryModalOpen(false)}
              onSave={handleSalarySave}
              currentSalary={empData?.salary || 0}
              employeeId={employeeId}
            />
            <AddPromotionModal
              isOpen={isPromoModalOpen}
              onClose={() => setIsPromoModalOpen(false)}
              onSave={handlePromoSave}
              currentDesignation={empData?.designation || ''}
              employeeId={employeeId}
            />
          </>
        )}
      </motion.div>
    </div>
  )
}
