import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, FolderKanban, Users, ShieldAlert, Award, Edit2, Archive, CheckCircle } from 'lucide-react'
import { listDepartments, createDepartment, updateDepartment, deactivateDepartment } from '../../api'
import { MetricCard } from '../../components/ui/MetricCard'
import { DepartmentModal } from '../../components/modals/DepartmentModal'
import toast from 'react-hot-toast'

export const DepartmentManagement = () => {
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedDept, setSelectedDept] = useState(null)

  useEffect(() => {
    fetchDepartments()
  }, [])

  const fetchDepartments = async () => {
    setLoading(true)
    try {
      const data = await listDepartments()
      setDepartments(data || [])
    } catch (err) {
      toast.error('Failed to load departments')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateNew = () => {
    setSelectedDept(null)
    setIsModalOpen(true)
  }

  const handleEdit = (dept) => {
    setSelectedDept(dept)
    setIsModalOpen(true)
  }

  const handleSave = async (payload) => {
    try {
      if (selectedDept) {
        await updateDepartment(selectedDept.id, payload)
        toast.success('Department updated successfully')
      } else {
        await createDepartment(payload)
        toast.success('Department created successfully')
      }
      fetchDepartments()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save department')
      throw err
    }
  }

  const handleDeactivate = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate this department?')) return
    try {
      await deactivateDepartment(id)
      toast.success('Department deactivated')
      fetchDepartments()
    } catch (err) {
      toast.error('Failed to deactivate department')
    }
  }

  const handleActivate = async (dept) => {
    try {
      await updateDepartment(dept.id, { is_active: true })
      toast.success('Department activated')
      fetchDepartments()
    } catch (err) {
      toast.error('Failed to activate department')
    }
  }

  const totalCount = departments.length
  const activeCount = departments.filter((d) => d.is_active).length

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Department Management</h1>
          <p className="text-slate-500 text-sm">Organize and manage structural departments and their respective heads.</p>
        </div>
        <button
          onClick={handleCreateNew}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-indigo px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-brand-indigo-hover transition self-start sm:self-auto cursor-pointer"
        >
          <Plus size={16} />
          New Department
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetricCard
          title="Total Departments"
          value={totalCount}
          icon={FolderKanban}
          description="Registered company business units"
        />
        <MetricCard
          title="Active Units"
          value={activeCount}
          icon={CheckCircle}
          description="Operational departments"
        />
      </div>

      {/* Grid of Department Cards */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
          <span className="text-slate-500 text-sm">Retrieving departments...</span>
        </div>
      ) : departments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center border border-slate-200 rounded-2xl bg-white shadow-sm">
          <FolderKanban className="text-slate-400 mb-4" size={48} />
          <h3 className="text-lg font-medium text-slate-800 mb-1">No departments found</h3>
          <p className="text-slate-500 text-sm max-w-xs">Get started by creating your first company department unit.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <AnimatePresence>
            {departments.map((dept, index) => (
              <motion.div
                key={dept.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.2, delay: index * 0.03 }}
                className={`flex flex-col justify-between rounded-2xl border p-6 bg-white transition-all ${
                  dept.is_active ? 'border-slate-200 hover:border-brand-indigo hover:shadow-md' : 'border-red-200 bg-red-50/50 opacity-70'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h3 className="text-lg font-semibold text-slate-900 tracking-tight">{dept.name}</h3>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                      dept.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                    }`}>
                      {dept.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <p className="text-slate-500 text-sm mb-6 line-clamp-2 h-10">
                    {dept.description || 'No description provided.'}
                  </p>
                </div>

                <div className="space-y-4 border-t border-slate-100 pt-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Department Head:</span>
                    <span className="font-medium text-slate-700">
                      {dept.head_name || 'Not Assigned'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Total Employees:</span>
                    <span className="inline-flex items-center gap-1 font-semibold text-brand-indigo">
                      <Users size={12} />
                      {dept.employee_count}
                    </span>
                  </div>

                  {/* Action Controls */}
                  <div className="flex gap-2 justify-end pt-2 border-t border-slate-100/50">
                    <button
                      onClick={() => handleEdit(dept)}
                      className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-700 transition cursor-pointer"
                      title="Edit"
                    >
                      <Edit2 size={14} />
                    </button>
                    {dept.is_active ? (
                      <button
                        onClick={() => handleDeactivate(dept.id)}
                        className="rounded-lg p-2 text-red-600 hover:bg-red-50 hover:text-red-700 transition cursor-pointer"
                        title="Deactivate"
                      >
                        <Archive size={14} />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivate(dept)}
                        className="rounded-lg p-2 text-green-600 hover:bg-green-50 hover:text-green-700 transition cursor-pointer"
                        title="Activate"
                      >
                        <CheckCircle size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Department Modal */}
      <DepartmentModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedDept(null)
        }}
        onSave={handleSave}
        department={selectedDept}
      />
    </div>
  )
}
