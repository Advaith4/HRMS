import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Award, ArrowRight, User, Calendar, Plus, Search } from 'lucide-react'
import { getRecentPromotions, listEmployees, addPromotion } from '../../api'
import { AddPromotionModal } from '../../components/modals/AddPromotionModal'
import { MetricCard } from '../../components/ui/MetricCard'
import toast from 'react-hot-toast'

export const PromotionDashboard = () => {
  const [promotions, setPromotions] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Search query for employee selection list
  const [search, setSearch] = useState('')

  // Modal States
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedEmp, setSelectedEmp] = useState(null)
  
  // Active Tab: 'history' or 'promote'
  const [activeTab, setActiveTab] = useState('history')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const history = await getRecentPromotions()
      const emps = await listEmployees()
      setPromotions(history || [])
      setEmployees(emps || [])
    } catch (err) {
      toast.error('Failed to load promotions dashboard')
    } finally {
      setLoading(false)
    }
  }

  const handlePromoteClick = (emp) => {
    setSelectedEmp(emp)
    setIsModalOpen(true)
  }

  const handlePromotionSubmit = async (employeeId, payload) => {
    try {
      await addPromotion(employeeId, payload)
      toast.success('Employee promoted successfully!')
      fetchData() // Refresh list
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit promotion')
      throw err
    }
  }

  // Filter employees for the promotion target list
  const filteredEmployees = employees.filter((e) => {
    const term = search.toLowerCase()
    return (
      (e.full_name || e.username || '').toLowerCase().includes(term) ||
      (e.employee_code || '').toLowerCase().includes(term) ||
      (e.department || '').toLowerCase().includes(term)
    )
  })

  // Stats calculation
  const totalPromotions = promotions.length
  const thisMonthPromotions = promotions.filter((p) => {
    const promoDate = new Date(p.promotion_date)
    const now = new Date()
    return promoDate.getMonth() === now.getMonth() && promoDate.getFullYear() === now.getFullYear()
  }).length

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Promotions & Advancements</h1>
          <p className="text-slate-500 text-sm">Track designation changes and submit employee advancement requests.</p>
        </div>
        <button
          onClick={() => setActiveTab('promote')}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-indigo px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-brand-indigo-hover transition self-start sm:self-auto cursor-pointer"
        >
          <Plus size={16} />
          Promote Employee
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <MetricCard
          title="Total Advancements"
          value={totalPromotions}
          icon={Award}
          description="Designation shifts recorded"
        />
        <MetricCard
          title="Promotions This Month"
          value={thisMonthPromotions}
          icon={Calendar}
          description="Current billing cycle confirmations"
        />
      </div>

      {/* Tab Selectors */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('history')}
          className={`pb-4 text-sm font-medium transition-colors relative cursor-pointer ${
            activeTab === 'history' ? 'text-brand-indigo font-bold' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Recent Activity
          {activeTab === 'history' && (
            <motion.div layoutId="promoTabUnderline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-indigo" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('promote')}
          className={`pb-4 text-sm font-medium transition-colors relative cursor-pointer ${
            activeTab === 'promote' ? 'text-brand-indigo font-bold' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Select Employee to Promote
          {activeTab === 'promote' && (
            <motion.div layoutId="promoTabUnderline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-indigo" />
          )}
        </button>
      </div>

      {/* Tab Panels */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
          <span className="text-slate-500 text-sm">Retrieving promotions logs...</span>
        </div>
      ) : activeTab === 'history' ? (
        /* History logs */
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {promotions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <Award className="text-slate-400 mb-4" size={48} />
              <h3 className="text-lg font-medium text-slate-800 mb-1">No promotions recorded</h3>
              <p className="text-slate-500 text-sm max-w-xs">Once you promote an employee, records will appear here.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm text-slate-700">
                <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-4">Employee</th>
                    <th className="px-6 py-4">Advancement Shift</th>
                    <th className="px-6 py-4">Effective Date</th>
                    <th className="px-6 py-4">Approved By</th>
                    <th className="px-6 py-4">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <AnimatePresence>
                    {promotions.map((p, idx) => (
                      <motion.tr
                        key={p.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.15, delay: idx * 0.02 }}
                        className="hover:bg-slate-50/80 transition-colors"
                      >
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {p.employee_username}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2 text-slate-600">
                            <span className="text-xs text-slate-400 line-through">{p.old_designation}</span>
                            <ArrowRight size={12} className="text-brand-indigo" />
                            <span className="font-semibold text-slate-900">{p.new_designation}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-slate-500 font-mono text-xs">
                          {new Date(p.promotion_date).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric'
                          })}
                        </td>
                        <td className="px-6 py-4 text-slate-700">
                          {p.approved_by_username}
                        </td>
                        <td className="px-6 py-4 text-slate-500 text-xs max-w-xs truncate" title={p.reason}>
                          {p.reason}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Employee search list */
        <div className="space-y-4">
          <div className="relative w-full max-w-md">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
              <Search size={16} />
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 py-2.5 text-slate-800 placeholder-slate-400 focus:border-brand-indigo focus:outline-none transition shadow-inner"
              placeholder="Search employee by name, code or department..."
            />
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            {filteredEmployees.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <User className="text-slate-400 mb-4" size={48} />
                <h3 className="text-lg font-medium text-slate-800 mb-1">No employees found</h3>
                <p className="text-slate-500 text-sm">No matches found for "{search}"</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm text-slate-700">
                  <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4">Code</th>
                      <th className="px-6 py-4">Name</th>
                      <th className="px-6 py-4">Department</th>
                      <th className="px-6 py-4">Current Designation</th>
                      <th className="px-6 py-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredEmployees.map((emp) => (
                      <tr key={emp.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-6 py-4 font-mono text-slate-500 font-medium">
                          {emp.employee_code}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {emp.full_name || emp.username}
                        </td>
                        <td className="px-6 py-4 text-slate-600">
                          {emp.department || 'Not Set'}
                        </td>
                        <td className="px-6 py-4 text-slate-500">
                          {emp.designation || 'Not Set'}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => handlePromoteClick(emp)}
                            className="inline-flex items-center gap-1 rounded-lg bg-brand-indigo px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-indigo-hover transition cursor-pointer"
                          >
                            Promote
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Promotion Modal */}
      {selectedEmp && (
        <AddPromotionModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false)
            setSelectedEmp(null)
          }}
          onSave={handlePromotionSubmit}
          currentDesignation={selectedEmp.designation}
          employeeId={selectedEmp.id}
        />
      )}
    </div>
  )
}
