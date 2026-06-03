import React, { useState } from 'react'
import { X } from 'lucide-react'
import toast from 'react-hot-toast'

export const CreateTicketModal = ({ isOpen, onClose, onSave }) => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('HR Issue')
  const [priority, setPriority] = useState('Medium')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim()) {
      toast.error('Title is required')
      return
    }
    if (!description.trim()) {
      toast.error('Description is required')
      return
    }
    setLoading(true)
    try {
      const payload = {
        title,
        description,
        category,
        priority,
      }
      await onSave(payload)
      setTitle('')
      setDescription('')
      setCategory('HR Issue')
      setPriority('Medium')
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit ticket')
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
            Raise Grievance / Ticket
          </h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Ticket Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
              placeholder="e.g. Discrepancy in leave balance"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
              >
                <option value="HR Issue">HR Issue</option>
                <option value="Leave Issue">Leave Issue</option>
                <option value="Salary Issue">Salary Issue</option>
                <option value="Workplace Concern">Workplace Concern</option>
                <option value="Manager Concern">Manager Concern</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Detailed Description *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows="4"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition resize-none"
              placeholder="Describe your issue, query or request in detail..."
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
              {loading ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
