import React from 'react'
import { StatusPill } from './ui/StatusPill'

export const EmployeeProfileSection = ({
  isEditingProfile,
  setIsEditingProfile,
  loadingProfile,
  profileData,
  user,
  editPhone,
  setEditPhone,
  editEmergencyContact,
  setEditEmergencyContact,
  editAddress,
  setEditAddress,
  editSkills,
  setEditSkills,
  handleUpdateProfile,
}) => {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border-custom bg-bg-surface p-6">
        <div className="flex justify-between items-center border-b border-border-custom pb-4 mb-6">
          <div>
            <h4 className="text-sm font-semibold text-txt-primary">Personal & Professional Records</h4>
            <p className="text-[11px] text-txt-secondary">Official employee file and records</p>
          </div>
          <button
            onClick={() => setIsEditingProfile(!isEditingProfile)}
            className="px-3 py-1.5 border border-border-custom text-xs font-semibold text-txt-secondary hover:text-brand-indigo hover:border-brand-indigo/30 bg-bg-page rounded-lg cursor-pointer transition-colors"
          >
            {isEditingProfile ? 'Cancel' : 'Edit Contact Info'}
          </button>
        </div>

        {loadingProfile ? (
          <div className="flex justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent" />
          </div>
        ) : profileData ? (
          isEditingProfile ? (
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Mobile Phone</label>
                  <input
                    type="text"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3.5 py-1.5 text-xs rounded-xl text-txt-primary"
                    placeholder="e.g. +91 98765 43210"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Emergency Contact</label>
                  <input
                    type="text"
                    value={editEmergencyContact}
                    onChange={(e) => setEditEmergencyContact(e.target.value)}
                    className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3.5 py-1.5 text-xs rounded-xl text-txt-primary"
                    placeholder="e.g. John Doe - Parent (+91 99999 88888)"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Residential Address</label>
                <textarea
                  rows={2}
                  value={editAddress}
                  onChange={(e) => setEditAddress(e.target.value)}
                  className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3.5 py-1.5 text-xs rounded-xl text-txt-primary resize-none"
                  placeholder="Street, City, Zip"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-txt-tertiary uppercase block">Skills (comma-separated)</label>
                <input
                  type="text"
                  value={editSkills}
                  onChange={(e) => setEditSkills(e.target.value)}
                  className="w-full bg-bg-page border border-border-custom focus:border-brand-indigo outline-none px-3.5 py-1.5 text-xs rounded-xl text-txt-primary"
                  placeholder="React, Node.js, Python"
                />
              </div>
              <div className="flex gap-2 justify-end pt-4 border-t border-border-custom">
                <button
                  type="submit"
                  className="h-8 px-4 bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold rounded-lg flex items-center justify-center cursor-pointer transition-all active:scale-98"
                >
                  Save Changes
                </button>
              </div>
            </form>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Left Column: Personal */}
              <div className="space-y-4">
                <h5 className="text-xs font-bold text-brand-indigo uppercase tracking-wider">Personal Information</h5>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Full Name</span>
                    <span className="text-txt-primary font-medium">{profileData.full_name || user?.username}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Email Address</span>
                    <span className="text-txt-primary font-medium">{profileData.email || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Mobile Phone</span>
                    <span className="text-txt-primary font-medium">{profileData.phone || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Date of Birth</span>
                    <span className="text-txt-primary font-medium">
                      {profileData.date_of_birth ? new Date(profileData.date_of_birth).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="text-xs">
                  <span className="text-txt-tertiary block font-semibold mb-1">Residential Address</span>
                  <span className="text-txt-primary font-medium">{profileData.address || 'N/A'}</span>
                </div>
                <div className="text-xs">
                  <span className="text-txt-tertiary block font-semibold mb-1">Emergency Contact</span>
                  <span className="text-txt-primary font-medium">{profileData.emergency_contact || 'N/A'}</span>
                </div>
              </div>

              {/* Right Column: Professional */}
              <div className="space-y-4">
                <h5 className="text-xs font-bold text-brand-indigo uppercase tracking-wider">Professional Information</h5>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Employee Code</span>
                    <span className="text-txt-primary font-medium">{profileData.employee_code}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Current Status</span>
                    <span className="text-txt-primary font-medium">
                      <StatusPill status={profileData.status || 'Active'} />
                    </span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Department</span>
                    <span className="text-txt-primary font-medium">{profileData.department || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Designation</span>
                    <span className="text-txt-primary font-medium">{profileData.designation || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Reporting Manager</span>
                    <span className="text-txt-primary font-medium">{profileData.manager_name || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-txt-tertiary block font-semibold mb-1">Work Location</span>
                    <span className="text-txt-primary font-medium">{profileData.work_location || 'N/A'}</span>
                  </div>
                </div>
                <div className="text-xs">
                  <span className="text-txt-tertiary block font-semibold mb-1">Certifications</span>
                  <span className="text-txt-primary font-medium">{profileData.certifications || 'None recorded'}</span>
                </div>
                <div className="text-xs">
                  <span className="text-txt-tertiary block font-semibold mb-1">Years of Experience</span>
                  <span className="text-txt-primary font-medium">{profileData.years_of_experience ?? 'N/A'} yrs</span>
                </div>
              </div>
            </div>
          )
        ) : (
          <div className="text-center py-6 text-xs text-txt-tertiary">Failed to load profile record.</div>
        )}
      </div>
    </div>
  )
}

export default EmployeeProfileSection
