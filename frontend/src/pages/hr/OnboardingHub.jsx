import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Archive, CheckCircle2, Plus, UserPlus } from 'lucide-react'
import { EmptyState } from '../../components/ui/EmptyState'
import { MetricCard } from '../../components/ui/MetricCard'
import { StatusPill } from '../../components/ui/StatusPill'
import {
  assignOnboardingTemplate,
  createOnboardingTemplate,
  deleteOnboardingTemplate,
  getOnboardingSummary,
  listEmployees,
  listOnboardingTemplates,
  updateOnboardingTemplate,
} from '../../api'

export const OnboardingHub = () => {
  const [summary, setSummary] = useState({})
  const [templates, setTemplates] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    name: '',
    description: '',
    task_title: '',
    task_description: '',
    due_date: '',
    employee_id: '',
    template_id: '',
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [summaryData, templateData, employeeData] = await Promise.all([
        getOnboardingSummary(),
        listOnboardingTemplates(),
        listEmployees(),
      ])
      setSummary(summaryData || {})
      setTemplates(templateData || [])
      setEmployees(employeeData || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load onboarding data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleCreateTemplate = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.task_title.trim()) {
      toast.error('Template name and first task are required')
      return
    }
    try {
      await createOnboardingTemplate({
        name: form.name.trim(),
        description: form.description.trim(),
        tasks: [{
          title: form.task_title.trim(),
          description: form.task_description.trim(),
          required: true,
          display_order: 1,
        }],
      })
      toast.success('Onboarding template created')
      setForm((prev) => ({ ...prev, name: '', description: '', task_title: '', task_description: '' }))
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to create template')
    }
  }

  const handleAssign = async (e) => {
    e.preventDefault()
    if (!form.employee_id || !form.template_id) {
      toast.error('Select an employee and template')
      return
    }
    try {
      await assignOnboardingTemplate({
        employee_id: Number(form.employee_id),
        template_id: Number(form.template_id),
        due_date: form.due_date || null,
      })
      toast.success('Onboarding plan assigned')
      setForm((prev) => ({ ...prev, employee_id: '', template_id: '', due_date: '' }))
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to assign onboarding')
    }
  }

  const handleRename = async (template) => {
    const name = window.prompt('Template name', template.name)
    if (!name || name.trim() === template.name) return
    try {
      await updateOnboardingTemplate(template.id, { name: name.trim() })
      toast.success('Template updated')
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to update template')
    }
  }

  const handleArchive = async (templateId) => {
    if (!window.confirm('Archive this onboarding template?')) return
    try {
      await deleteOnboardingTemplate(templateId)
      toast.success('Template archived')
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to archive template')
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard iconName="UserCheck" label="New Joiners" value={summary.new_joiners || 0} delta="This month" />
        <MetricCard iconName="ClipboardList" label="Active Plans" value={summary.active_plans || 0} delta="In progress" />
        <MetricCard iconName="Award" label="Completed Plans" value={summary.completed_plans || 0} delta="Closed" hoverColor="teal" />
        <MetricCard iconName="CalendarCheck" label="Overdue Plans" value={summary.overdue_plans || 0} delta="Needs action" />
      </div>

      <div className="rounded-xl border border-brand-indigo/20 bg-brand-indigo-muted/30 p-5">
        <h4 className="text-sm font-semibold text-txt-primary">Employee Onboarding</h4>
        <p className="text-xs text-txt-secondary mt-1 leading-relaxed">
          Employee Onboarding helps new hires complete required documentation, company formalities, policy acknowledgements, and role preparation before becoming fully operational.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <form onSubmit={handleCreateTemplate} className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
          <div className="border-b border-border-custom pb-3">
            <h4 className="text-sm font-semibold">Create Onboarding Template</h4>
            <p className="text-[11px] text-txt-secondary">Start with one required task, then edit the template as needed.</p>
          </div>
          <input className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" placeholder="Template name" value={form.name} onChange={(e) => updateField('name', e.target.value)} />
          <textarea className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo resize-none" rows={2} placeholder="Description" value={form.description} onChange={(e) => updateField('description', e.target.value)} />
          <input className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" placeholder="First task title" value={form.task_title} onChange={(e) => updateField('task_title', e.target.value)} />
          <textarea className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo resize-none" rows={2} placeholder="Task description" value={form.task_description} onChange={(e) => updateField('task_description', e.target.value)} />
          <button className="h-9 bg-brand-indigo text-white text-xs font-semibold px-4 rounded-lg flex items-center gap-2">
            <Plus size={14} />
            Create Template
          </button>
        </form>

        <form onSubmit={handleAssign} className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
          <div className="border-b border-border-custom pb-3">
            <h4 className="text-sm font-semibold">Assign Onboarding Plan</h4>
            <p className="text-[11px] text-txt-secondary">Assign one template to one employee.</p>
          </div>
          <select className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.employee_id} onChange={(e) => updateField('employee_id', e.target.value)}>
            <option value="">Select employee</option>
            {employees.map((employee) => (
              <option key={employee.id} value={employee.id}>{employee.username || employee.employee_code} · {employee.employee_code}</option>
            ))}
          </select>
          <select className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.template_id} onChange={(e) => updateField('template_id', e.target.value)}>
            <option value="">Select template</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>{template.name}</option>
            ))}
          </select>
          <input type="date" className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo" value={form.due_date} onChange={(e) => updateField('due_date', e.target.value)} />
          <button className="h-9 bg-brand-indigo text-white text-xs font-semibold px-4 rounded-lg flex items-center gap-2">
            <UserPlus size={14} />
            Assign Plan
          </button>
        </form>
      </div>

      <div className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
        <div className="border-b border-border-custom pb-3">
          <h4 className="text-sm font-semibold">Templates</h4>
          <p className="text-[11px] text-txt-secondary">Manage active onboarding templates and their task lists.</p>
        </div>
        {loading ? (
          <div className="text-xs text-txt-tertiary py-8">Loading onboarding templates...</div>
        ) : templates.length === 0 ? (
          <EmptyState title="No templates yet" description="Create your first onboarding template to begin assigning plans." />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {templates.map((template) => (
              <div key={template.id} className="border border-border-custom rounded-xl p-4 bg-bg-page space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h5 className="text-sm font-semibold">{template.name}</h5>
                    <p className="text-[11px] text-txt-secondary mt-1">{template.description || 'No description'}</p>
                  </div>
                  <StatusPill status={template.is_active ? 'Active' : 'Archived'} />
                </div>
                <div className="space-y-2">
                  {template.tasks.map((task) => (
                    <div key={task.id} className="flex items-center gap-2 text-xs text-txt-secondary">
                      <CheckCircle2 size={13} className="text-success-primary shrink-0" />
                      <span>{task.title}</span>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end gap-2 pt-2 border-t border-border-custom">
                  <button onClick={() => handleRename(template)} className="px-3 py-1.5 text-[11px] border border-border-custom rounded-lg">Edit</button>
                  <button onClick={() => handleArchive(template.id)} className="px-3 py-1.5 text-[11px] border border-danger-primary/30 text-danger-primary rounded-lg flex items-center gap-1">
                    <Archive size={12} />
                    Archive
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default OnboardingHub
