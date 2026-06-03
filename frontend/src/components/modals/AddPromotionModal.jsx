import React, { useState, useEffect } from 'react'
import { X, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'

export const AddPromotionModal = ({ isOpen, onClose, onSave, currentDesignation = '', employeeId }) => {
  const [newDesignation, setNewDesignation] = useState('')
  const [promotionDate, setPromotionDate] = useState(new Date().toISOString().split('T')[0])
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setNewDesignation('')
      setReason('')
      setPromotionDate(new Date().toISOString().split('T')[0])
    }
  }, [isOpen])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!newDesignation.trim()) {
      toast.error('New designation is required')
      return
    }
    setLoading(true)
    try {
      await onSave(employeeId, {
        new_designation: newDesignation,
        promotion_date: promotionDate,
        reason,
      })
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit promotion')
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
            Promote Employee
          </h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-xl bg-slate-50 p-4 border border-slate-100">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-semibold">Current Designation</div>
            <div className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <TrendingUp size={16} className="text-slate-400" />
              {currentDesignation || 'Not Set'}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              New Designation *
            </label>
            <input
              type="text"
              value={newDesignation}
              onChange={(e) => setNewDesignation(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
              placeholder="e.g. Principal Software Engineer"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Promotion Date *
            </label>
            <input
              type="date"
              value={promotionDate}
              onChange={(e) => setPromotionDate(e.target.value)}
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
              placeholder="e.g. Strong leadership on Project X and technical mastery."
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
              {loading ? 'Submitting...' : 'Confirm Promotion'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
