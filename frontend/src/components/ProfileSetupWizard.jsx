import React, { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { FileUp, Save, ShieldCheck } from 'lucide-react'
import {
  getMyProfileCompletion,
  updateCandidateProfile,
  updateEmployeeCompletionProfile,
  uploadProfileDocument,
} from '../api'

const candidateInitial = {
  full_name: '', phone: '', date_of_birth: '', gender: '', location: '', address: '',
  linkedin_url: '', portfolio_url: '', current_status: '', current_company: '',
  current_role: '', years_of_experience: 0, expected_salary: '', notice_period: '',
  degree: '', institution: '', graduation_year: '', cgpa_percentage: '',
  technical_skills: '', soft_skills: '', certifications: '',
}

const employeeInitial = {
  phone: '', address: '', emergency_contact: '', blood_group: '', marital_status: '',
  previous_experience: '', skills: '', certifications: '', career_interests: '', career_goals: '',
}

const Field = ({ label, children }) => (
  <label className="space-y-1">
    <span className="text-[10px] uppercase font-bold text-txt-tertiary">{label}</span>
    {children}
  </label>
)

const inputClass = 'w-full bg-bg-page border border-border-custom rounded-lg px-3 py-2 text-xs outline-none focus:border-brand-indigo text-txt-primary'

export const ProfileSetupWizard = ({ role, onComplete }) => {
  const isCandidate = role === 'candidate'
  const [step, setStep] = useState(0)
  const [profile, setProfile] = useState(isCandidate ? candidateInitial : employeeInitial)
  const [documents, setDocuments] = useState([])
  const [completion, setCompletion] = useState(0)
  const [missing, setMissing] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const steps = useMemo(() => (
    isCandidate
      ? ['Personal', 'Professional', 'Education', 'Skills', 'Documents']
      : ['Personal', 'Professional', 'Documents']
  ), [isCandidate])

  const fetchProfile = async () => {
    setLoading(true)
    try {
      const data = await getMyProfileCompletion()
      const p = data.profile || {}
      setProfile({ ...(isCandidate ? candidateInitial : employeeInitial), ...p })
      setDocuments(p.documents || [])
      setCompletion(p.completion_percent || 0)
      setMissing(p.missing_information || [])
      if (p.is_complete) onComplete?.()
    } catch (err) {
      console.error(err)
      toast.error('Failed to load profile setup')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfile()
  }, [])

  const updateField = (key, value) => setProfile((prev) => ({ ...prev, [key]: value }))

  const saveProfile = async () => {
    setSaving(true)
    try {
      const payload = isCandidate
        ? await updateCandidateProfile(profile)
        : await updateEmployeeCompletionProfile(profile)
      setCompletion(payload.completion_percent || 0)
      setMissing(payload.missing_information || [])
      setDocuments(payload.documents || documents)
      toast.success('Profile saved')
      if (payload.is_complete) onComplete?.()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  const handleUpload = async (documentType, file) => {
    if (!file) return
    try {
      await uploadProfileDocument(documentType, file)
      toast.success(`${documentType} uploaded`)
      fetchProfile()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Upload failed')
    }
  }

  if (loading) {
    return <div className="rounded-xl border border-border-custom bg-bg-surface p-8 text-sm text-txt-secondary">Loading profile setup...</div>
  }

  return (
    <div className="min-h-[70vh] rounded-xl border border-border-custom bg-bg-surface p-6 space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-border-custom pb-4">
        <div>
          <div className="flex items-center gap-2 text-brand-indigo">
            <ShieldCheck size={18} />
            <h3 className="text-lg font-bold">{isCandidate ? 'Career Profile Setup' : 'Employee Profile Setup'}</h3>
          </div>
          <p className="text-xs text-txt-secondary mt-1">
            Complete this one-time setup so TalentForge can maintain accurate workforce records and document readiness.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-36 h-2 bg-bg-page border border-border-custom rounded-full overflow-hidden">
            <div className="h-full bg-brand-indigo" style={{ width: `${completion}%` }} />
          </div>
          <span className="text-sm font-bold text-brand-indigo">{completion}%</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {steps.map((name, idx) => (
          <button key={name} onClick={() => setStep(idx)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${step === idx ? 'bg-brand-indigo text-white border-brand-indigo' : 'border-border-custom text-txt-secondary bg-bg-page'}`}>
            {idx + 1}. {name}
          </button>
        ))}
      </div>

      {missing.length > 0 && (
        <div className="rounded-lg border border-warning-primary/20 bg-warning-bg/30 p-3 text-xs text-warning-primary">
          Missing: {missing.slice(0, 8).join(', ')}{missing.length > 8 ? '...' : ''}
        </div>
      )}

      <div className="space-y-4">
        {isCandidate && step === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Full Name"><input className={inputClass} value={profile.full_name || ''} onChange={(e) => updateField('full_name', e.target.value)} /></Field>
            <Field label="Phone"><input className={inputClass} value={profile.phone || ''} onChange={(e) => updateField('phone', e.target.value)} /></Field>
            <Field label="Date of Birth"><input type="date" className={inputClass} value={profile.date_of_birth || ''} onChange={(e) => updateField('date_of_birth', e.target.value)} /></Field>
            <Field label="Gender"><input className={inputClass} value={profile.gender || ''} onChange={(e) => updateField('gender', e.target.value)} /></Field>
            <Field label="Location"><input className={inputClass} value={profile.location || ''} onChange={(e) => updateField('location', e.target.value)} /></Field>
            <Field label="LinkedIn URL"><input className={inputClass} value={profile.linkedin_url || ''} onChange={(e) => updateField('linkedin_url', e.target.value)} /></Field>
            <Field label="Portfolio URL"><input className={inputClass} value={profile.portfolio_url || ''} onChange={(e) => updateField('portfolio_url', e.target.value)} /></Field>
            <Field label="Address"><textarea rows={2} className={inputClass} value={profile.address || ''} onChange={(e) => updateField('address', e.target.value)} /></Field>
          </div>
        )}

        {isCandidate && step === 1 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Current Status"><select className={inputClass} value={profile.current_status || ''} onChange={(e) => updateField('current_status', e.target.value)}><option value="">Select</option><option>Student</option><option>Fresher</option><option>Employed</option><option>Seeking Opportunities</option></select></Field>
            <Field label="Current Company"><input className={inputClass} value={profile.current_company || ''} onChange={(e) => updateField('current_company', e.target.value)} /></Field>
            <Field label="Current Role"><input className={inputClass} value={profile.current_role || ''} onChange={(e) => updateField('current_role', e.target.value)} /></Field>
            <Field label="Years of Experience"><input type="number" className={inputClass} value={profile.years_of_experience ?? 0} onChange={(e) => updateField('years_of_experience', Number(e.target.value))} /></Field>
            <Field label="Expected Salary"><input className={inputClass} value={profile.expected_salary || ''} onChange={(e) => updateField('expected_salary', e.target.value)} /></Field>
            <Field label="Notice Period"><input className={inputClass} value={profile.notice_period || ''} onChange={(e) => updateField('notice_period', e.target.value)} /></Field>
          </div>
        )}

        {isCandidate && step === 2 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Degree"><input className={inputClass} value={profile.degree || ''} onChange={(e) => updateField('degree', e.target.value)} /></Field>
            <Field label="Institution"><input className={inputClass} value={profile.institution || ''} onChange={(e) => updateField('institution', e.target.value)} /></Field>
            <Field label="Graduation Year"><input className={inputClass} value={profile.graduation_year || ''} onChange={(e) => updateField('graduation_year', e.target.value)} /></Field>
            <Field label="CGPA / Percentage"><input className={inputClass} value={profile.cgpa_percentage || ''} onChange={(e) => updateField('cgpa_percentage', e.target.value)} /></Field>
          </div>
        )}

        {isCandidate && step === 3 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Technical Skills"><textarea rows={4} className={inputClass} value={profile.technical_skills || ''} onChange={(e) => updateField('technical_skills', e.target.value)} /></Field>
            <Field label="Soft Skills"><textarea rows={4} className={inputClass} value={profile.soft_skills || ''} onChange={(e) => updateField('soft_skills', e.target.value)} /></Field>
            <Field label="Certifications"><textarea rows={4} className={inputClass} value={profile.certifications || ''} onChange={(e) => updateField('certifications', e.target.value)} /></Field>
          </div>
        )}

        {!isCandidate && step === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Phone"><input className={inputClass} value={profile.phone || ''} onChange={(e) => updateField('phone', e.target.value)} /></Field>
            <Field label="Emergency Contact"><input className={inputClass} value={profile.emergency_contact || ''} onChange={(e) => updateField('emergency_contact', e.target.value)} /></Field>
            <Field label="Blood Group"><input className={inputClass} value={profile.blood_group || ''} onChange={(e) => updateField('blood_group', e.target.value)} /></Field>
            <Field label="Marital Status"><input className={inputClass} value={profile.marital_status || ''} onChange={(e) => updateField('marital_status', e.target.value)} /></Field>
            <Field label="Address"><textarea rows={3} className={inputClass} value={profile.address || ''} onChange={(e) => updateField('address', e.target.value)} /></Field>
          </div>
        )}

        {!isCandidate && step === 1 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Previous Experience"><textarea rows={3} className={inputClass} value={profile.previous_experience || ''} onChange={(e) => updateField('previous_experience', e.target.value)} /></Field>
            <Field label="Skills"><textarea rows={3} className={inputClass} value={profile.skills || ''} onChange={(e) => updateField('skills', e.target.value)} /></Field>
            <Field label="Certifications"><textarea rows={3} className={inputClass} value={profile.certifications || ''} onChange={(e) => updateField('certifications', e.target.value)} /></Field>
            <Field label="Career Interests"><textarea rows={3} className={inputClass} value={profile.career_interests || ''} onChange={(e) => updateField('career_interests', e.target.value)} /></Field>
            <Field label="Career Goals"><textarea rows={3} className={inputClass} value={profile.career_goals || ''} onChange={(e) => updateField('career_goals', e.target.value)} /></Field>
          </div>
        )}

        {step === steps.length - 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(isCandidate ? ['Resume', 'Certifications', 'Academic Documents'] : ['Government ID', 'Resume', 'Educational Certificates', 'Experience Letters', 'Other Supporting Documents']).map((docType) => (
                <label key={docType} className="rounded-xl border border-border-custom bg-bg-page p-4 cursor-pointer hover:border-brand-indigo/40">
                  <div className="flex items-center gap-2 text-xs font-semibold">
                    <FileUp size={15} className="text-brand-indigo" />
                    {docType}
                  </div>
                  <input type="file" className="hidden" onChange={(e) => handleUpload(docType, e.target.files?.[0])} />
                </label>
              ))}
            </div>
            <div className="rounded-xl border border-border-custom overflow-hidden">
              {(documents || []).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between px-4 py-3 border-b border-border-custom last:border-b-0 text-xs">
                  <span>{doc.document_type} · {doc.original_filename}</span>
                  <span className="font-semibold text-brand-indigo">{doc.verification_status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-border-custom">
        <button disabled={step === 0} onClick={() => setStep((s) => Math.max(s - 1, 0))} className="px-4 py-2 border border-border-custom rounded-lg text-xs font-semibold disabled:opacity-40">Back</button>
        <div className="flex gap-2">
          <button onClick={saveProfile} disabled={saving} className="px-4 py-2 bg-brand-indigo text-white rounded-lg text-xs font-semibold inline-flex items-center gap-2">
            <Save size={14} />
            Save
          </button>
          <button disabled={step === steps.length - 1} onClick={() => setStep((s) => Math.min(s + 1, steps.length - 1))} className="px-4 py-2 border border-border-custom rounded-lg text-xs font-semibold disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  )
}

export default ProfileSetupWizard
