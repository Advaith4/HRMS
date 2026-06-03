import React, { useState, useEffect } from 'react'
import { X, IndianRupee } from 'lucide-react'
import toast from 'react-hot-toast'

export const AddSalaryModal = ({ isOpen, onClose, onSave, currentSalary = 0, employeeId }) => {
  const [newSalary, setNewSalary] = useState('')
  const [reason, setReason] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setNewSalary('')
      setReason('')
      setEffectiveDate(new Date().toISOString().split('T')[0])
    }
  }, [isOpen])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const salaryVal = parseFloat(newSalary)
    if (isNaN(salaryVal) || salaryVal <= 0) {
      toast.error('Please enter a valid salary')
      return
    }
    setLoading(true)
    try {
      await onSave(employeeId, {
        new_salary: salaryVal,
        reason,
        effective_date: effectiveDate,
      })
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to revise salary')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <h3 className="text-lg font-semibold text-slate-900">
            Add Salary Revision
          </h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-xl bg-slate-50 p-4 border border-slate-100">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-semibold">Current Salary</div>
            <div className="text-xl font-semibold text-slate-800 flex items-center gap-1">
              <IndianRupee size={18} className="text-slate-400" />
              {currentSalary ? currentSalary.toLocaleString('en-IN') : 'Not Set'}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              New Salary *
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                <IndianRupee size={16} />
              </span>
              <input
                type="number"
                value={newSalary}
                onChange={(e) => setNewSalary(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
                placeholder="e.g. 1500000"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Effective Date *
            </label>
            <input
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Reason / Remarks *
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows="3"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition resize-none"
              placeholder="e.g. Annual Appraisal / Promotion adjustment"
              required
            />
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t border-slate-100 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-200 bg-transparent px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-brand-indigo hover:bg-brand-indigo-hover px-5 py-2.5 text-sm font-semibold text-white shadow-md disabled:opacity-50 transition cursor-pointer"
            >
              {loading ? 'Submitting...' : 'Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
