import React, { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { listEmployees } from '../../api'
import toast from 'react-hot-toast'

export const DepartmentModal = ({ isOpen, onClose, onSave, department = null }) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [headUserId, setHeadUserId] = useState('')
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setName(department?.name || '')
      setDescription(department?.description || '')
      setHeadUserId(department?.head_user_id || '')
      fetchEmployees()
    }
  }, [isOpen, department])

  const fetchEmployees = async () => {
    try {
      const data = await listEmployees()
      setEmployees(data || [])
    } catch (err) {
      console.error('Failed to load employees', err)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) {
      toast.error('Department name is required')
      return
    }
    setLoading(true)
    try {
      const payload = {
        name,
        description,
        head_user_id: headUserId ? parseInt(headUserId) : null,
      }
      await onSave(payload)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save department')
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
            {department ? 'Edit Department' : 'Create Department'}
          </h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Department Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
              placeholder="e.g. Engineering"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows="3"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition resize-none"
              placeholder="Brief description of the department's charter"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
              Department Head
            </label>
            <select
              value={headUserId}
              onChange={(e) => setHeadUserId(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo focus:outline-none transition"
            >
              <option value="">Select Department Head</option>
              {employees.map((emp) => (
                <option key={emp.user_id} value={emp.user_id}>
                  {emp.username} (Code: {emp.employee_code})
                </option>
              ))}
            </select>
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
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
