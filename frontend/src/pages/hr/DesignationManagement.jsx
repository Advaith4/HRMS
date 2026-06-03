import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Award, Filter, Edit2, Archive, CheckCircle } from 'lucide-react'
import { listDesignations, createDesignation, updateDesignation, archiveDesignation, listDepartments } from '../../api'
import { DesignationModal } from '../../components/modals/DesignationModal'
import toast from 'react-hot-toast'

export const DesignationManagement = () => {
  const [designations, setDesignations] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [deptFilter, setDeptFilter] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedDesig, setSelectedDesig] = useState(null)

  useEffect(() => {
    fetchDesignations()
    fetchDepartments()
  }, [deptFilter])

  const fetchDesignations = async () => {
    setLoading(true)
    try {
      const data = await listDesignations(deptFilter || undefined)
      setDesignations(data || [])
    } catch (err) {
      toast.error('Failed to load designations')
    } finally {
      setLoading(false)
    }
  }

  const fetchDepartments = async () => {
    try {
      const data = await listDepartments()
      setDepartments(data || [])
    } catch (err) {
      console.error(err)
    }
  }

  const handleCreateNew = () => {
    setSelectedDesig(null)
    setIsModalOpen(true)
  }

  const handleEdit = (desig) => {
    setSelectedDesig(desig)
    setIsModalOpen(true)
  }

  const handleSave = async (payload) => {
    try {
      if (selectedDesig) {
        await updateDesignation(selectedDesig.id, payload)
        toast.success('Designation updated successfully')
      } else {
        await createDesignation(payload)
        toast.success('Designation created successfully')
      }
      fetchDesignations()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save designation')
      throw err
    }
  }

  const handleArchive = async (id) => {
    if (!window.confirm('Are you sure you want to archive this designation?')) return
    try {
      await archiveDesignation(id)
      toast.success('Designation archived')
      fetchDesignations()
    } catch (err) {
      toast.error('Failed to archive designation')
    }
  }

  const handleActivate = async (desig) => {
    try {
      await updateDesignation(desig.id, { is_active: true })
      toast.success('Designation activated')
      fetchDesignations()
    } catch (err) {
      toast.error('Failed to activate designation')
    }
  }

  // Get level badge colors
  const getLevelBadge = (level) => {
    if (level === 1) return 'bg-slate-100 text-slate-700 border-slate-200'
    if (level === 2) return 'bg-blue-50 text-blue-700 border-blue-200'
    if (level === 3) return 'bg-indigo-50 text-indigo-700 border-indigo-200'
    if (level === 4) return 'bg-amber-50 text-amber-800 border-amber-200'
    return 'bg-red-50 text-red-700 border-red-200'
  }

  const getLevelLabel = (level) => {
    if (level === 1) return 'Junior'
    if (level === 2) return 'Mid'
    if (level === 3) return 'Senior'
    if (level === 4) return 'Lead'
    return 'Director/Principal'
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Designation Management</h1>
          <p className="text-slate-500 text-sm">Define and grade employee designations, hierarchies and roles.</p>
        </div>
        <button
          onClick={handleCreateNew}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-indigo px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-brand-indigo-hover transition self-start sm:self-auto cursor-pointer"
        >
          <Plus size={16} />
          New Designation
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Filter size={16} />
          <span>Filter by Department:</span>
        </div>
        <select
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-slate-700 focus:border-brand-indigo focus:outline-none transition w-full sm:w-60 text-sm cursor-pointer"
        >
          <option value="">All Departments</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>

      {/* Designations Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
            <span className="text-slate-500 text-sm">Retrieving designations...</span>
          </div>
        ) : designations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Award className="text-slate-400 mb-4" size={48} />
            <h3 className="text-lg font-medium text-slate-800 mb-1">No designations found</h3>
            <p className="text-slate-500 text-sm max-w-xs">Start creating roles and designation levels for your org chart.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4">Designation Name</th>
                  <th className="px-6 py-4">Department</th>
                  <th className="px-6 py-4">Hierarchy Level</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <AnimatePresence>
                  {designations.map((desig, index) => (
                    <motion.tr
                      key={desig.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.15, delay: index * 0.02 }}
                      className={`hover:bg-slate-50/80 transition-colors ${!desig.is_active && 'opacity-70 bg-red-50/50'}`}
                    >
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900">{desig.name}</div>
                        <div className="text-xs text-slate-400 max-w-sm truncate">{desig.description || 'No description'}</div>
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {desig.department_name || 'Global / Common'}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${getLevelBadge(desig.level)}`}>
                          L{desig.level} — {getLevelLabel(desig.level)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                          desig.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                        }`}>
                          {desig.is_active ? 'Active' : 'Archived'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => handleEdit(desig)}
                            className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-700 transition cursor-pointer"
                            title="Edit"
                          >
                            <Edit2 size={14} />
                          </button>
                          {desig.is_active ? (
                            <button
                              onClick={() => handleArchive(desig.id)}
                              className="rounded-lg p-2 text-red-600 hover:bg-red-50 hover:text-red-700 transition cursor-pointer"
                              title="Archive"
                            >
                              <Archive size={14} />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleActivate(desig)}
                              className="rounded-lg p-2 text-green-600 hover:bg-green-50 hover:text-green-700 transition cursor-pointer"
                              title="Activate"
                            >
                              <CheckCircle size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Designation Modal */}
      <DesignationModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedDesig(null)
        }}
        onSave={handleSave}
        designation={selectedDesig}
      />
    </div>
  )
}
