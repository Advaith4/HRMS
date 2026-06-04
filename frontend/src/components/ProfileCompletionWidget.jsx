import React from 'react'
import { ShieldCheck, AlertCircle, ArrowRight, CheckCircle2, FileText, User } from 'lucide-react'

const FIELD_LABELS = {
  full_name: "Full Name",
  phone: "Phone Number",
  date_of_birth: "Date of Birth",
  gender: "Gender",
  location: "Location",
  address: "Address",
  linkedin_url: "LinkedIn Profile",
  portfolio_url: "Portfolio Website",
  current_status: "Current Status",
  current_company: "Current Company",
  current_role: "Current Role",
  years_of_experience: "Years of Experience",
  expected_salary: "Expected Salary",
  notice_period: "Notice Period",
  degree: "Degree",
  institution: "Institution",
  graduation_year: "Graduation Year",
  cgpa_percentage: "CGPA / Percentage",
  technical_skills: "Technical Skills",
  soft_skills: "Soft Skills",
  certifications: "Certifications",
  
  // Employee fields
  emergency_contact: "Emergency Contact",
  blood_group: "Blood Group",
  marital_status: "Marital Status",
  previous_experience: "Previous Work Experience",
  skills: "Skills",
  career_interests: "Career Interests",
  career_goals: "Career Goals"
}

export const ProfileCompletionWidget = ({ profileCompletion, onAction }) => {
  if (!profileCompletion) return null

  const completionPercent = profileCompletion.completion_percent ?? 0
  const isComplete = profileCompletion.is_complete ?? (completionPercent === 100)

  const missingFields = []
  const missingDocs = []

  const missingInfoList = profileCompletion.missing_information || []
  missingInfoList.forEach(item => {
    if (item.startsWith("document:")) {
      missingDocs.push(item.replace("document:", ""))
    } else {
      missingFields.push(FIELD_LABELS[item] || item.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" "))
    }
  })

  return (
    <div className="rounded-xl border border-border-custom bg-bg-surface p-6 shadow-md hover:shadow-lg transition-all duration-300 space-y-5 relative overflow-hidden group">
      {/* Dynamic background accent */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-brand-indigo/5 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-brand-indigo/8 transition-all duration-300" />
      
      <div className="flex items-center justify-between border-b border-border-custom/50 pb-3">
        <div className="flex items-center space-x-2">
          <div className={`p-2 rounded-lg ${isComplete ? 'bg-success-bg/20 text-success-primary' : 'bg-warning-bg/20 text-warning-primary'}`}>
            {isComplete ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-txt-secondary">Profile Readiness</h4>
            <p className="text-[10px] text-txt-tertiary mt-0.5">Keep your credentials up-to-date</p>
          </div>
        </div>
        <div>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${isComplete ? 'text-success-primary bg-success-bg/10 border-success-primary/20' : 'text-warning-primary bg-warning-bg/10 border-warning-primary/20'}`}>
            {isComplete ? 'Verified' : 'Action Required'}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {/* Progress bar container */}
        <div className="space-y-2">
          <div className="flex justify-between items-end">
            <span className="text-2xl font-black text-txt-primary tracking-tight">
              {completionPercent}% <span className="text-xs font-normal text-txt-secondary">Complete</span>
            </span>
          </div>
          <div className="w-full h-2.5 bg-bg-page border border-border-custom/50 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${isComplete ? 'bg-gradient-to-r from-green-500 to-emerald-400' : 'bg-gradient-to-r from-brand-indigo to-indigo-400'}`}
              style={{ width: `${completionPercent}%` }}
            />
          </div>
        </div>

        {/* Missing fields or success banner */}
        {!isComplete ? (
          <div className="space-y-3 pt-2">
            {missingFields.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider flex items-center gap-1.5">
                  <User size={12} className="text-brand-indigo" />
                  Missing Profile Information
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {missingFields.map((field, idx) => (
                    <span key={idx} className="inline-flex items-center text-[10px] bg-bg-page border border-border-custom px-2 py-0.5 rounded-md text-txt-secondary hover:border-brand-indigo/30 transition-colors">
                      <span className="w-1 h-1 rounded-full bg-warning-primary mr-1.5 animate-pulse" />
                      {field}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {missingDocs.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-bold text-txt-tertiary uppercase tracking-wider flex items-center gap-1.5">
                  <FileText size={12} className="text-brand-indigo" />
                  Required Uploads
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {missingDocs.map((doc, idx) => (
                    <span key={idx} className="inline-flex items-center text-[10px] bg-bg-page border border-border-custom px-2 py-0.5 rounded-md text-txt-secondary hover:border-brand-indigo/30 transition-colors">
                      <span className="w-1 h-1 rounded-full bg-red-400 mr-1.5 animate-pulse" />
                      {doc} Document
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-3">
              <button
                onClick={onAction}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-indigo hover:bg-brand-indigo/90 text-white rounded-lg text-xs font-semibold shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer"
              >
                Complete Profile Setup
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3 pt-2">
            <div className="rounded-lg bg-success-bg/10 border border-success-primary/20 p-3 text-xs text-success-primary flex items-start gap-2">
              <ShieldCheck size={16} className="mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-bold">All items completed</p>
                <p className="text-[11px] opacity-90 mt-0.5">Your official workforce records and verification documents are fully processed.</p>
              </div>
            </div>
            <div className="pt-1">
              <button
                onClick={onAction}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-bg-page border border-border-custom hover:border-brand-indigo/30 text-txt-secondary hover:text-txt-primary rounded-lg text-xs font-semibold transition-all cursor-pointer"
              >
                Review details
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ProfileCompletionWidget
