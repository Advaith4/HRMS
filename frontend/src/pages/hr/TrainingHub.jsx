import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Archive, Plus, UserPlus } from 'lucide-react'
import { EmptyState } from '../../components/ui/EmptyState'
import { MetricCard } from '../../components/ui/MetricCard'
import { StatusPill } from '../../components/ui/StatusPill'
import {
  archiveTrainingProgram,
  assignTraining,
  createTrainingProgram,
  getTrainingSummary,
  listEmployees,
  listTrainingPrograms,
  updateTrainingProgram,
} from '../../api'

export const TrainingHub = () => {
  const [editingProgramId, setEditingProgramId] = useState(null)
  const [editingProgramTitle, setEditingProgramTitle] = useState('')
  const [summary, setSummary] = useState({})
  const [programs, setPrograms] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    title: '',
    description: '',
    category: 'General',
    skills_covered: '',
    duration_hours: 1,
    difficulty: 'Beginner',
    status: 'Active',
    employee_id: '',
    program_id: '',
    due_date: '',
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [summaryData, programData, employeeData] = await Promise.all([
        getTrainingSummary(),
        listTrainingPrograms(),
        listEmployees(),
      ])
      setSummary(summaryData || {})
      setPrograms(programData || [])
      setEmployees(employeeData || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load training data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleCreateProgram = async (e) => {
    e.preventDefault()
    if (!form.title.trim()) {
      toast.error('Training title is required')
      return
    }
    try {
      await createTrainingProgram({
        title: form.title.trim(),
        description: form.description.trim(),
        category: form.category.trim() || 'General',
        skills_covered: form.skills_covered.trim(),
        duration_hours: Number(form.duration_hours) || 1,
        difficulty: form.difficulty,
        status: form.status,
      })
      toast.success('Training program created')
      setForm((prev) => ({ ...prev, title: '', description: '', skills_covered: '', duration_hours: 1 }))
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to create training program')
    }
  }

  const handleAssign = async (e) => {
    e.preventDefault()
    if (!form.employee_id || !form.program_id) {
      toast.error('Select an employee and program')
      return
    }
    try {
      await assignTraining({
        employee_id: Number(form.employee_id),
        program_id: Number(form.program_id),
        due_date: form.due_date || null,
      })
      toast.success('Training assigned')
      setForm((prev) => ({ ...prev, employee_id: '', program_id: '', due_date: '' }))
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to assign training')
    }
  }

  const handleSaveRename = async (programId) => {
    if (!editingProgramTitle.trim()) {
      toast.error('Program title cannot be empty')
      return
    }
    try {
      await updateTrainingProgram(programId, { title: editingProgramTitle.trim() })
      toast.success('Program updated')
      setEditingProgramId(null)
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update program')
    }
  }

  const handleArchive = async (programId) => {
    if (!window.confirm('Archive this training program?')) return
    try {
      await archiveTrainingProgram(programId)
      toast.success('Program archived')
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to archive program')
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard iconName="BookOpen" label="Active Programs" value={summary.active_programs || 0} delta="Available" />
        <MetricCard iconName="ClipboardList" label="Assignments" value={summary.assignments || 0} delta="Individual" />
        <MetricCard iconName="Award" label="Completion" value={`${summary.completion_percent || 0}%`} delta={`${summary.completed || 0} complete`} hoverColor="teal" />
        <MetricCard iconName="CalendarCheck" label="Overdue" value={summary.overdue || 0} delta="Needs review" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <form onSubmit={handleCreateProgram} className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
          <div className="border-b border-border-custom pb-3">
            <h4 className="text-sm font-semibold">Create Training Program</h4>
            <p className="text-[11px] text-txt-secondary">Simple training catalog entry for individual assignment.</p>
          </div>
          <input className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" placeholder="Training title" value={form.title} onChange={(e) => updateField('title', e.target.value)} />
          <textarea className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo resize-none" rows={2} placeholder="Description" value={form.description} onChange={(e) => updateField('description', e.target.value)} />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className="bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" placeholder="Category" value={form.category} onChange={(e) => updateField('category', e.target.value)} />
            <input type="number" min="1" className="bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.duration_hours} onChange={(e) => updateField('duration_hours', e.target.value)} />
            <select className="bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.difficulty} onChange={(e) => updateField('difficulty', e.target.value)}>
              <option>Beginner</option>
              <option>Intermediate</option>
              <option>Advanced</option>
            </select>
          </div>
          <input className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" placeholder="Skills covered, comma-separated" value={form.skills_covered} onChange={(e) => updateField('skills_covered', e.target.value)} />
          <button className="h-9 bg-brand-indigo text-white text-xs font-semibold px-4 rounded-lg flex items-center gap-2">
            <Plus size={14} />
            Create Program
          </button>
        </form>

        <form onSubmit={handleAssign} className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
          <div className="border-b border-border-custom pb-3">
            <h4 className="text-sm font-semibold">Assign Training</h4>
            <p className="text-[11px] text-txt-secondary">Phase 2A supports individual employee assignment only.</p>
          </div>
          <select className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.employee_id} onChange={(e) => updateField('employee_id', e.target.value)}>
            <option value="">Select employee</option>
            {employees.map((employee) => (
              <option key={employee.id} value={employee.id}>{employee.username || employee.employee_code} · {employee.employee_code}</option>
            ))}
          </select>
          <select className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.program_id} onChange={(e) => updateField('program_id', e.target.value)}>
            <option value="">Select program</option>
            {programs.filter((program) => program.status !== 'Archived').map((program) => (
              <option key={program.id} value={program.id}>{program.title}</option>
            ))}
          </select>
          <input type="date" className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.due_date} onChange={(e) => updateField('due_date', e.target.value)} />
          <button className="h-9 bg-brand-indigo text-white text-xs font-semibold px-4 rounded-lg flex items-center gap-2">
            <UserPlus size={14} />
            Assign Training
          </button>
        </form>
      </div>

      <div className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
        <div className="border-b border-border-custom pb-3">
          <h4 className="text-sm font-semibold">Training Programs</h4>
          <p className="text-[11px] text-txt-secondary">Create, edit, and archive programs from the catalog.</p>
        </div>
        {loading ? (
          <div className="text-xs text-txt-tertiary py-8">Loading training programs...</div>
        ) : programs.length === 0 ? (
          <EmptyState title="No training programs" description="Create a program before assigning training to employees." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-bg-page text-txt-tertiary uppercase text-[10px]">
                  <th className="py-2.5 px-3">Program</th>
                  <th className="py-2.5 px-3">Skills</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-custom/50">
                {programs.map((program) => {
                  const isEditing = editingProgramId === program.id
                  return (
                    <tr key={program.id}>
                      <td className="py-3 px-3">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editingProgramTitle}
                            onChange={(e) => setEditingProgramTitle(e.target.value)}
                            className="bg-bg-page border border-brand-indigo outline-none px-2 py-1 text-xs rounded-lg text-txt-primary w-full max-w-xs focus:border-brand-indigo"
                          />
                        ) : (
                          <>
                            <span className="font-semibold block">{program.title}</span>
                            <span className="text-[10px] text-txt-secondary">{program.category} · {program.difficulty}</span>
                          </>
                        )}
                      </td>
                      <td className="py-3 px-3 text-txt-secondary">{program.skills_covered || 'General'}</td>
                      <td className="py-3 px-3 text-txt-secondary">{program.duration_hours}h</td>
                      <td className="py-3 px-3"><StatusPill status={program.status} /></td>
                      <td className="py-3 px-3 text-right space-x-2">
                        {isEditing ? (
                          <>
                            <button onClick={() => handleSaveRename(program.id)} className="px-3 py-1.5 text-[11px] bg-brand-indigo text-white rounded-lg font-semibold cursor-pointer">Save</button>
                            <button onClick={() => setEditingProgramId(null)} className="px-3 py-1.5 text-[11px] border border-border-custom rounded-lg cursor-pointer">Cancel</button>
                          </>
                        ) : (
                          <>
                            <button onClick={() => { setEditingProgramId(program.id); setEditingProgramTitle(program.title); }} className="px-3 py-1.5 text-[11px] border border-border-custom rounded-lg cursor-pointer">Edit</button>
                            <button onClick={() => handleArchive(program.id)} className="px-3 py-1.5 text-[11px] border border-danger-primary/30 text-danger-primary rounded-lg inline-flex items-center gap-1 cursor-pointer">
                              <Archive size={12} />
                              Archive
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default TrainingHub
