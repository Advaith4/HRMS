import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Archive, CheckCircle2, Plus, UserPlus, X, Edit, Trash2, FileText, Check } from 'lucide-react'
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
  addOnboardingTask,
  updateOnboardingTask,
  deleteOnboardingTask,
} from '../../api'

const STANDARD_DOC_TYPES = [
  'Government ID',
  'Resume',
  'Educational Certificates',
  'Experience Letters',
  'Academic Documents',
  'Certifications'
]

export const OnboardingHub = () => {
  const [summary, setSummary] = useState({})
  const [templates, setTemplates] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Assign plan form state
  const [assignForm, setAssignForm] = useState({
    employee_id: '',
    template_id: '',
    due_date: '',
  })

  // Modal Editor state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState('create') // 'create' | 'edit'
  const [editingTemplateId, setEditingTemplateId] = useState(null)
  
  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    tasks: [],
    required_documents: [],
    deletedTaskIds: []
  })

  const [customDocType, setCustomDocType] = useState('')

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

  const handleAssign = async (e) => {
    e.preventDefault()
    if (!assignForm.employee_id || !assignForm.template_id) {
      toast.error('Select an employee and template')
      return
    }
    try {
      await assignOnboardingTemplate({
        employee_id: Number(assignForm.employee_id),
        template_id: Number(assignForm.template_id),
        due_date: assignForm.due_date || null,
      })
      toast.success('Onboarding plan assigned')
      setAssignForm({ employee_id: '', template_id: '', due_date: '' })
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to assign onboarding')
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

  // Open Template Modal
  const openCreateModal = () => {
    setModalMode('create')
    setEditingTemplateId(null)
    setTemplateForm({
      name: '',
      description: '',
      tasks: [{ title: 'Submit Documents', description: 'Upload requested files', required: true, display_order: 1 }],
      required_documents: ['Resume'],
      deletedTaskIds: []
    })
    setIsModalOpen(true)
  }

  const openEditModal = (template) => {
    setModalMode('edit')
    setEditingTemplateId(template.id)
    setTemplateForm({
      id: template.id,
      name: template.name,
      description: template.description || '',
      tasks: (template.tasks || []).map(t => ({ ...t, isDirty: false })),
      required_documents: template.required_documents || [],
      deletedTaskIds: []
    })
    setIsModalOpen(true)
  }

  // Manage tasks inside Modal
  const handleAddTask = () => {
    setTemplateForm(prev => ({
      ...prev,
      tasks: [
        ...prev.tasks,
        {
          title: '',
          description: '',
          required: true,
          display_order: prev.tasks.length + 1
        }
      ]
    }))
  }

  const handleUpdateTaskField = (index, key, val) => {
    setTemplateForm(prev => {
      const updatedTasks = [...prev.tasks]
      updatedTasks[index] = {
        ...updatedTasks[index],
        [key]: val,
        isDirty: true
      }
      return { ...prev, tasks: updatedTasks }
    })
  }

  const handleRemoveTask = (index) => {
    setTemplateForm(prev => {
      const updatedTasks = [...prev.tasks]
      const removedTask = updatedTasks.splice(index, 1)[0]
      const deletedIds = [...prev.deletedTaskIds]
      if (removedTask && removedTask.id) {
        deletedIds.push(removedTask.id)
      }
      return { ...prev, tasks: updatedTasks, deletedTaskIds: deletedIds }
    })
  }

  // Manage documents inside Modal
  const handleToggleDocument = (docType) => {
    setTemplateForm(prev => {
      const docs = [...prev.required_documents]
      const idx = docs.indexOf(docType)
      if (idx > -1) {
        docs.splice(idx, 1)
      } else {
        docs.push(docType)
      }
      return { ...prev, required_documents: docs }
    })
  }

  const handleAddCustomDocument = () => {
    if (!customDocType.trim()) return
    const cleaned = customDocType.trim()
    if (!templateForm.required_documents.includes(cleaned)) {
      setTemplateForm(prev => ({
        ...prev,
        required_documents: [...prev.required_documents, cleaned]
      }))
    }
    setCustomDocType('')
  }

  const handleRemoveDocument = (docType) => {
    setTemplateForm(prev => ({
      ...prev,
      required_documents: prev.required_documents.filter(d => d !== docType)
    }))
  }

  // Save changes
  const handleSaveTemplate = async (e) => {
    e.preventDefault()
    if (!templateForm.name.trim()) {
      toast.error('Template name is required')
      return
    }
    if (templateForm.tasks.length === 0) {
      toast.error('Template requires at least one task')
      return
    }
    if (templateForm.tasks.some(t => !t.title.trim())) {
      toast.error('All tasks must have a title')
      return
    }

    const saveToast = toast.loading(modalMode === 'create' ? 'Creating template...' : 'Saving changes...')
    try {
      if (modalMode === 'create') {
        await createOnboardingTemplate({
          name: templateForm.name.trim(),
          description: templateForm.description.trim(),
          tasks: templateForm.tasks.map(t => ({
            title: t.title.trim(),
            description: t.description.trim(),
            required: t.required,
            display_order: t.display_order
          })),
          required_documents: templateForm.required_documents
        })
        toast.success('Onboarding template created', { id: saveToast })
      } else {
        // Edit flow
        // 1. Update basic details and documents
        await updateOnboardingTemplate(editingTemplateId, {
          name: templateForm.name.trim(),
          description: templateForm.description.trim(),
          required_documents: templateForm.required_documents
        })

        // 2. Delete tasks removed in the wizard editor
        for (const taskId of templateForm.deletedTaskIds) {
          await deleteOnboardingTask(taskId)
        }

        // 3. Create or update tasks
        for (const t of templateForm.tasks) {
          if (!t.id) {
            await addOnboardingTask(editingTemplateId, {
              title: t.title.trim(),
              description: t.description.trim(),
              required: t.required,
              display_order: t.display_order
            })
          } else if (t.isDirty) {
            await updateOnboardingTask(t.id, {
              title: t.title.trim(),
              description: t.description.trim(),
              required: t.required,
              display_order: t.display_order
            })
          }
        }
        toast.success('Onboarding template updated', { id: saveToast })
      }
      setIsModalOpen(false)
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save template', { id: saveToast })
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

      <div className="rounded-xl border border-brand-indigo/20 bg-brand-indigo-muted/30 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-semibold text-txt-primary">Employee Onboarding Hub</h4>
          <p className="text-xs text-txt-secondary mt-1 leading-relaxed max-w-3xl">
            Design onboarding workflows that specify required compliance documents (such as Identity papers) and custom tasks (such as Meet Manager). Auto-calculate progress via submissions and task completion.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="bg-brand-indigo hover:bg-brand-indigo/90 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2 transition-all shrink-0 self-start sm:self-center"
        >
          <Plus size={14} />
          Create Template
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Templates list on the left (wide) */}
        <div className="xl:col-span-2 rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
          <div className="border-b border-border-custom pb-3 flex justify-between items-center">
            <div>
              <h4 className="text-sm font-semibold">Active Templates</h4>
              <p className="text-[11px] text-txt-secondary">Manage tasks and required document templates.</p>
            </div>
          </div>
          {loading ? (
            <div className="text-xs text-txt-tertiary py-8 text-center">Loading templates...</div>
          ) : templates.length === 0 ? (
            <EmptyState title="No templates yet" description="Create your first onboarding template to begin assigning plans." />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {templates.map((template) => (
                <div key={template.id} className="border border-border-custom rounded-xl p-4 bg-bg-page flex flex-col justify-between gap-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h5 className="text-sm font-semibold">{template.name}</h5>
                        <p className="text-[11px] text-txt-secondary mt-1">{template.description || 'No description'}</p>
                      </div>
                      <StatusPill status={template.is_active ? 'Active' : 'Archived'} />
                    </div>

                    {/* Required Documents in template */}
                    {template.required_documents && template.required_documents.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[9px] uppercase font-bold text-txt-tertiary">Required Documents</span>
                        <div className="flex flex-wrap gap-1">
                          {template.required_documents.map(docType => (
                            <span key={docType} className="text-[9px] bg-brand-indigo/10 border border-brand-indigo/25 text-brand-indigo px-1.5 py-0.5 rounded font-medium">
                              {docType}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Tasks list */}
                    <div className="space-y-1.5">
                      <span className="text-[9px] uppercase font-bold text-txt-tertiary">Tasks Checklist</span>
                      <div className="space-y-1">
                        {(template.tasks || []).map((task) => (
                          <div key={task.id} className="flex items-start gap-2 text-xs text-txt-secondary">
                            <CheckCircle2 size={13} className="text-success-primary shrink-0 mt-0.5" />
                            <span className="leading-tight">
                              {task.title} {task.required && <span className="text-red-400 font-bold" title="Required">*</span>}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-2 border-t border-border-custom">
                    <button
                      onClick={() => openEditModal(template)}
                      className="px-3 py-1.5 text-[11px] border border-border-custom rounded-lg hover:border-brand-indigo/40 inline-flex items-center gap-1.5"
                    >
                      <Edit size={12} />
                      Edit Template
                    </button>
                    <button
                      onClick={() => handleArchive(template.id)}
                      className="px-3 py-1.5 text-[11px] border border-danger-primary/30 text-danger-primary rounded-lg flex items-center gap-1 hover:bg-danger-bg/10"
                    >
                      <Archive size={12} />
                      Archive
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Assign Form on the right (narrow) */}
        <form onSubmit={handleAssign} className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4 self-start">
          <div className="border-b border-border-custom pb-3">
            <h4 className="text-sm font-semibold">Assign Onboarding Plan</h4>
            <p className="text-[11px] text-txt-secondary">Manually assign a plan to a team member.</p>
          </div>
          <div className="space-y-3">
            <label className="block space-y-1">
              <span className="text-[10px] uppercase font-bold text-txt-tertiary">Employee</span>
              <select
                className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                value={assignForm.employee_id}
                onChange={(e) => setAssignForm(prev => ({ ...prev, employee_id: e.target.value }))}
              >
                <option value="">Select employee</option>
                {employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.full_name || employee.username} ({employee.employee_code})</option>
                ))}
              </select>
            </label>

            <label className="block space-y-1">
              <span className="text-[10px] uppercase font-bold text-txt-tertiary">Onboarding Template</span>
              <select
                className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                value={assignForm.template_id}
                onChange={(e) => setAssignForm(prev => ({ ...prev, template_id: e.target.value }))}
              >
                <option value="">Select template</option>
                {templates.filter(t => t.is_active).map((template) => (
                  <option key={template.id} value={template.id}>{template.name}</option>
                ))}
              </select>
            </label>

            <label className="block space-y-1">
              <span className="text-[10px] uppercase font-bold text-txt-tertiary">Due Date</span>
              <input
                type="date"
                className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                value={assignForm.due_date}
                onChange={(e) => setAssignForm(prev => ({ ...prev, due_date: e.target.value }))}
              />
            </label>
          </div>
          <button className="w-full h-9 bg-brand-indigo hover:bg-brand-indigo/90 text-white text-xs font-semibold px-4 rounded-lg flex items-center justify-center gap-2 transition-all">
            <UserPlus size={14} />
            Assign Onboarding Plan
          </button>
        </form>
      </div>

      {/* Template Modal Editor */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="relative w-full max-w-3xl h-[85vh] rounded-xl border border-border-custom bg-bg-surface flex flex-col overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border-custom bg-bg-page">
              <div>
                <h3 className="text-sm font-bold text-txt-primary">
                  {modalMode === 'create' ? 'Create Onboarding Template' : 'Edit Onboarding Template'}
                </h3>
                <p className="text-[10px] text-txt-secondary">Specify required documents and procedural steps.</p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg hover:bg-bg-page border border-transparent hover:border-border-custom text-txt-secondary hover:text-txt-primary transition-all"
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable Form */}
            <form onSubmit={handleSaveTemplate} className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Basic details */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-1">
                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase font-bold text-txt-tertiary">Template Name</span>
                    <input
                      className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                      placeholder="e.g. Standard Developer"
                      value={templateForm.name}
                      onChange={(e) => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                      required
                    />
                  </label>
                </div>
                <div className="md:col-span-2">
                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase font-bold text-txt-tertiary">Description</span>
                    <input
                      className="w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                      placeholder="Details about this plan..."
                      value={templateForm.description}
                      onChange={(e) => setTemplateForm(prev => ({ ...prev, description: e.target.value }))}
                    />
                  </label>
                </div>
              </div>

              {/* Required Documents Manager */}
              <div className="space-y-3">
                <div className="border-b border-border-custom pb-1.5 flex items-center justify-between">
                  <span className="text-xs font-bold text-txt-primary flex items-center gap-1.5">
                    <FileText size={14} className="text-brand-indigo" />
                    Required Documents Checklist
                  </span>
                  <span className="text-[10px] text-txt-secondary">
                    {templateForm.required_documents.length} document types configured
                  </span>
                </div>
                
                {/* Standard selectors */}
                <div className="flex flex-wrap gap-2">
                  {STANDARD_DOC_TYPES.map(docType => {
                    const isSelected = templateForm.required_documents.includes(docType)
                    return (
                      <button
                        type="button"
                        key={docType}
                        onClick={() => handleToggleDocument(docType)}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-semibold border flex items-center gap-1.5 transition-all ${
                          isSelected
                            ? 'bg-brand-indigo/15 text-brand-indigo border-brand-indigo'
                            : 'border-border-custom text-txt-secondary bg-bg-page hover:border-border-custom/80'
                        }`}
                      >
                        {isSelected && <Check size={10} />}
                        {docType}
                      </button>
                    )
                  })}
                </div>

                {/* Custom Documents input */}
                <div className="flex gap-2 max-w-md pt-1">
                  <input
                    className="flex-1 bg-bg-page border border-border-custom rounded-lg px-3 py-1.5 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                    placeholder="Add custom required document type..."
                    value={customDocType}
                    onChange={(e) => setCustomDocType(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddCustomDocument(); } }}
                  />
                  <button
                    type="button"
                    onClick={handleAddCustomDocument}
                    className="px-3 bg-bg-page border border-border-custom hover:border-brand-indigo/40 rounded-lg text-xs font-semibold"
                  >
                    Add
                  </button>
                </div>

                {/* Selected Custom documents */}
                {templateForm.required_documents.filter(d => !STANDARD_DOC_TYPES.includes(d)).length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {templateForm.required_documents
                      .filter(d => !STANDARD_DOC_TYPES.includes(d))
                      .map(docType => (
                        <span key={docType} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-brand-indigo/10 border border-brand-indigo/20 text-brand-indigo text-[10px] font-medium">
                          {docType}
                          <button type="button" onClick={() => handleRemoveDocument(docType)} className="hover:text-red-400">
                            <X size={10} />
                          </button>
                        </span>
                      ))}
                  </div>
                )}
              </div>

              {/* Tasks List Manager */}
              <div className="space-y-4">
                <div className="border-b border-border-custom pb-1.5 flex items-center justify-between">
                  <span className="text-xs font-bold text-txt-primary flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-brand-indigo" />
                    Procedural Tasks List ({templateForm.tasks.length})
                  </span>
                  <button
                    type="button"
                    onClick={handleAddTask}
                    className="text-[10px] text-brand-indigo hover:underline flex items-center gap-1"
                  >
                    <Plus size={12} />
                    Add Task Step
                  </button>
                </div>

                <div className="space-y-3">
                  {templateForm.tasks.map((task, index) => (
                    <div key={index} className="flex gap-4 p-4 border border-border-custom bg-bg-page/50 rounded-xl items-start relative hover:border-border-custom/80">
                      <span className="text-xs font-bold text-txt-tertiary bg-bg-page px-2 py-1 border border-border-custom rounded shrink-0">
                        Step {index + 1}
                      </span>
                      
                      <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div className="md:col-span-2">
                          <input
                            className="w-full bg-bg-page border border-border-custom rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                            placeholder="Task Title (e.g. Complete Orientation)"
                            value={task.title}
                            onChange={(e) => handleUpdateTaskField(index, 'title', e.target.value)}
                            required
                          />
                        </div>
                        <div className="md:col-span-2">
                          <input
                            className="w-full bg-bg-page border border-border-custom rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-brand-indigo text-txt-primary"
                            placeholder="Brief details (Optional)"
                            value={task.description}
                            onChange={(e) => handleUpdateTaskField(index, 'description', e.target.value)}
                          />
                        </div>
                        <div className="md:col-span-2 flex items-center gap-4">
                          <label className="flex items-center gap-1.5 text-xs text-txt-secondary cursor-pointer">
                            <input
                              type="checkbox"
                              checked={task.required}
                              onChange={(e) => handleUpdateTaskField(index, 'required', e.target.checked)}
                            />
                            Required task
                          </label>
                        </div>
                        <div className="md:col-span-2 flex items-center justify-between">
                          <label className="flex items-center gap-1.5 text-[10px] text-txt-tertiary uppercase font-bold">
                            Display Order
                            <input
                              type="number"
                              className="w-14 bg-bg-page border border-border-custom rounded px-2 py-0.5 text-xs outline-none"
                              value={task.display_order}
                              onChange={(e) => handleUpdateTaskField(index, 'display_order', Number(e.target.value))}
                            />
                          </label>
                          <button
                            type="button"
                            onClick={() => handleRemoveTask(index)}
                            className="p-1 rounded text-red-400 hover:bg-red-500/10 hover:text-red-500"
                            title="Delete Task Step"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border-custom bg-bg-surface">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-border-custom rounded-lg text-xs font-semibold hover:bg-bg-page transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-indigo hover:bg-brand-indigo/90 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-2 transition-all"
                >
                  Save Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default OnboardingHub
