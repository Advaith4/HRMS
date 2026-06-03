import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, UserCheck, Users, Calendar, Shield, Briefcase, Eye, ChevronDown } from 'lucide-react'
import { listEmployeeDirectory, listDepartments } from '../../api'
import { StatusPill } from '../../components/ui/StatusPill'
import { MetricCard } from '../../components/ui/MetricCard'
import { EmployeeProfileDrawer } from '../../components/drawers/EmployeeProfileDrawer'

export const EmployeeDirectory = () => {
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)

  // Filters & Search
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sort, setSort] = useState('joining_date')

  // Selected employee for Drawer
  const [selectedEmpId, setSelectedEmpId] = useState(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  useEffect(() => {
    fetchDirectory()
    fetchDepts()
  }, [search, deptFilter, statusFilter, sort])

  const fetchDirectory = async () => {
    setLoading(true)
    try {
      const data = await listEmployeeDirectory({
        search: search || undefined,
        department: deptFilter || undefined,
        status: statusFilter || undefined,
        sort: sort || undefined,
      })
      setEmployees(data || [])
    } catch (err) {
      console.error('Failed to load directory', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchDepts = async () => {
    try {
      const depts = await listDepartments()
      setDepartments(depts || [])
    } catch (err) {
      console.error('Failed to fetch departments', err)
    }
  }

  // Calculate quick stats from employees list
  const totalCount = employees.length
  const activeCount = employees.filter((e) => e.status === 'Active').length
  const leaveCount = employees.filter((e) => e.status === 'On Leave').length
  const probationCount = employees.filter((e) => e.status === 'Probation').length

  const handleRowClick = (employeeId) => {
    setSelectedEmpId(employeeId)
    setIsDrawerOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Employee Directory</h1>
          <p className="text-slate-500 text-sm">Monitor, search and manage core employee records and lifecycles.</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Employees"
          value={totalCount}
          icon={Users}
          description="Registered team members"
        />
        <MetricCard
          title="Active Status"
          value={activeCount}
          icon={UserCheck}
          description="Currently working"
          trend="+2 this month"
        />
        <MetricCard
          title="On Probation"
          value={probationCount}
          icon={Shield}
          description="In review phase"
        />
        <MetricCard
          title="On Leave"
          value={leaveCount}
          icon={Calendar}
          description="Out of office"
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row gap-4 items-center bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="relative w-full lg:w-96">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
            <Search size={16} />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 py-2.5 text-slate-800 placeholder-slate-400 focus:border-brand-indigo focus:outline-none transition shadow-inner"
            placeholder="Search name, code, email..."
          />
        </div>

        <div className="flex flex-wrap gap-3 items-center w-full lg:w-auto lg:ml-auto">
          {/* Department Filter */}
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-slate-700 focus:border-brand-indigo focus:outline-none transition text-sm cursor-pointer"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-slate-700 focus:border-brand-indigo focus:outline-none transition text-sm cursor-pointer"
          >
            <option value="">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Probation">Probation</option>
            <option value="On Leave">On Leave</option>
            <option value="Resigned">Resigned</option>
            <option value="Terminated">Terminated</option>
          </select>

          {/* Sort Filter */}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-slate-700 focus:border-brand-indigo focus:outline-none transition text-sm cursor-pointer"
          >
            <option value="joining_date">Sort: Joining Date</option>
            <option value="department">Sort: Department</option>
            <option value="designation">Sort: Designation</option>
          </select>
        </div>
      </div>

      {/* Directory Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
            <span className="text-slate-500 text-sm">Retrieving employee roster...</span>
          </div>
        ) : employees.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Users className="text-slate-400 mb-4" size={48} />
            <h3 className="text-lg font-medium text-slate-800 mb-1">No employees found</h3>
            <p className="text-slate-500 text-sm max-w-xs">Try adjusting your filters or search terms.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4">Employee ID</th>
                  <th className="px-6 py-4">Name</th>
                  <th className="px-6 py-4">Department</th>
                  <th className="px-6 py-4">Designation</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Joining Date</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <AnimatePresence>
                  {employees.map((emp, index) => (
                    <motion.tr
                      key={emp.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.15, delay: index * 0.02 }}
                      onClick={() => handleRowClick(emp.id)}
                      className="group hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4 font-mono text-slate-500 font-medium">
                        {emp.employee_code}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900">{emp.full_name || emp.username}</div>
                        <div className="text-xs text-slate-400">{emp.email}</div>
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {emp.department || 'Not Set'}
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {emp.designation || 'Not Set'}
                      </td>
                      <td className="px-6 py-4">
                        <StatusPill status={emp.status || 'Active'} />
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                        {emp.joining_date ? new Date(emp.joining_date).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric'
                        }) : 'N/A'}
                      </td>
                      <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleRowClick(emp.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-brand-indigo hover:text-white hover:border-brand-indigo transition cursor-pointer"
                        >
                          <Eye size={12} />
                          View Profile
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Profile Drawer */}
      <EmployeeProfileDrawer
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false)
          setSelectedEmpId(null)
          fetchDirectory() // Refresh in case of changes
        }}
        employeeId={selectedEmpId}
      />
    </div>
  )
}
