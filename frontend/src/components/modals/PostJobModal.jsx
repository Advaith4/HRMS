import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { X, Briefcase, DollarSign, Award, MapPin } from 'lucide-react'
import { createJob, updateJob } from '../../api/jobs'
import toast from 'react-hot-toast'

export const PostJobModal = ({ isOpen, onClose, jobToEdit, onSaveSuccess }) => {
  const isEdit = !!jobToEdit

  // Form Fields
  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('')
  const [description, setDescription] = useState('')
  const [requiredSkills, setRequiredSkills] = useState('')
  const [salaryRange, setSalaryRange] = useState('')
  const [experienceRequired, setExperienceRequired] = useState('')
  
  // Validation Errors
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Populate data when editing
  useEffect(() => {
    if (jobToEdit) {
      setTitle(jobToEdit.title || '')
      setDepartment(jobToEdit.department || '')
      setDescription(jobToEdit.description || '')
      setRequiredSkills(jobToEdit.required_skills || '')
      setSalaryRange(jobToEdit.salary_range || '')
      setExperienceRequired(jobToEdit.experience_required || '')
    } else {
      setTitle('')
      setDepartment('')
      setDescription('')
      setRequiredSkills('')
      setSalaryRange('')
      setExperienceRequired('')
    }
    setErrors({})
  }, [jobToEdit, isOpen])

  if (!isOpen) return null

  const validate = () => {
    const tempErrors = {}
    if (!title.trim()) tempErrors.title = 'Title is required'
    if (!department.trim()) tempErrors.department = 'Department is required'
    if (!description.trim()) tempErrors.description = 'Description is required'
    if (!requiredSkills.trim()) tempErrors.requiredSkills = 'At least one skill is required'
    if (!salaryRange.trim()) tempErrors.salaryRange = 'Salary range is required (e.g. ₹6–10 LPA)'
    if (!experienceRequired.trim()) tempErrors.experienceRequired = 'Experience description is required'
    
    setErrors(tempErrors)
    return Object.keys(tempErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setIsSubmitting(true)
    const payload = {
      title: title.trim(),
      department: department.trim(),
      description: description.trim(),
      required_skills: requiredSkills.trim(),
      salary_range: salaryRange.trim(),
      experience_required: experienceRequired.trim(),
    }

    try {
      let savedJob
      if (isEdit) {
        savedJob = await updateJob(jobToEdit.id, payload)
        toast.success('Job details updated successfully!')
      } else {
        savedJob = await createJob(payload)
        toast.success('Job posted successfully!')
      }
      if (onSaveSuccess) onSaveSuccess(savedJob)
      onClose()
    } catch (err) {
      console.error(err)
      toast.error('Failed to save job posting. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Card Wrapper */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-2xl bg-bg-elevated border border-border-hover-custom rounded-2xl p-6 relative z-10 shadow-2xl space-y-4 text-txt-primary select-none max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-border-custom">
          <div>
            <h3 className="text-base font-semibold">
              {isEdit ? 'Modify Job Posting' : 'Create New Job Posting'}
            </h3>
            <p className="text-xs text-txt-secondary mt-1">
              {isEdit ? 'Update details for the current job listing' : 'Publish a new position to the candidate boards'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-txt-secondary hover:text-txt-primary transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          
          <div className="grid grid-cols-2 gap-4">
            {/* Job Title */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-txt-secondary uppercase">Job Title</label>
              <input
                type="text"
                placeholder="e.g. Lead Backend Engineer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className={`w-full bg-bg-page border focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary transition-colors ${
                  errors.title ? 'border-danger-primary' : 'border-border-custom'
                }`}
              />
              {errors.title && <span className="text-[10px] text-danger-primary font-medium">{errors.title}</span>}
            </div>

            {/* Department */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-txt-secondary uppercase">Department</label>
              <input
                type="text"
                placeholder="e.g. Engineering"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className={`w-full bg-bg-page border focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary transition-colors ${
                  errors.department ? 'border-danger-primary' : 'border-border-custom'
                }`}
              />
              {errors.department && <span className="text-[10px] text-danger-primary font-medium">{errors.department}</span>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Salary Range */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-txt-secondary uppercase">Salary Range</label>
              <input
                type="text"
                placeholder="e.g. ₹12–18 LPA"
                value={salaryRange}
                onChange={(e) => setSalaryRange(e.target.value)}
                className={`w-full bg-bg-page border focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary transition-colors ${
                  errors.salaryRange ? 'border-danger-primary' : 'border-border-custom'
                }`}
              />
              {errors.salaryRange && <span className="text-[10px] text-danger-primary font-medium">{errors.salaryRange}</span>}
            </div>

            {/* Experience Required */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-txt-secondary uppercase">Experience Required</label>
              <input
                type="text"
                placeholder="e.g. 3-5 years"
                value={experienceRequired}
                onChange={(e) => setExperienceRequired(e.target.value)}
                className={`w-full bg-bg-page border focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary transition-colors ${
                  errors.experienceRequired ? 'border-danger-primary' : 'border-border-custom'
                }`}
              />
              {errors.experienceRequired && <span className="text-[10px] text-danger-primary font-medium">{errors.experienceRequired}</span>}
            </div>
          </div>

          {/* Required Skills (Comma-separated) */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-txt-secondary uppercase">Required Skills (Comma separated)</label>
            <input
              type="text"
              placeholder="Python, FastAPI, SQLModel, PostgreSQL, Docker"
              value={requiredSkills}
              onChange={(e) => setRequiredSkills(e.target.value)}
              className={`w-full bg-bg-page border focus:border-brand-indigo outline-none px-3 py-1.5 text-xs rounded-lg text-txt-primary transition-colors ${
                errors.requiredSkills ? 'border-danger-primary' : 'border-border-custom'
              }`}
            />
            {errors.requiredSkills && <span className="text-[10px] text-danger-primary font-medium">{errors.requiredSkills}</span>}
            <span className="text-[10px] text-txt-tertiary block">Use commas to split skills pill chips on candidate screening views.</span>
          </div>

          {/* Description */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-txt-secondary uppercase">Job Description & expectations</label>
            <textarea
              rows={6}
              placeholder="Outline role responsibilities, expectations, and day-to-day operations..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={`w-full bg-bg-page border focus:border-brand-indigo outline-none px-3 py-2 text-xs rounded-lg text-txt-primary transition-colors resize-none ${
                errors.description ? 'border-danger-primary' : 'border-border-custom'
              }`}
            />
            {errors.description && <span className="text-[10px] text-danger-primary font-medium">{errors.description}</span>}
          </div>

          {/* Submit Actions */}
          <div className="flex items-center space-x-3 justify-end pt-4 border-t border-border-custom">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 border border-border-custom text-txt-secondary hover:text-txt-primary text-xs font-semibold rounded-lg hover:bg-bg-page transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-1.5 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-1.5 active:scale-98 transition-all disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Saving position...' : isEdit ? 'Update Posting' : 'Publish Job'}
            </button>
          </div>

        </form>
      </motion.div>
    </div>
  )
}
export default PostJobModal
