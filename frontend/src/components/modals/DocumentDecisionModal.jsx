import React, { useState, useEffect } from 'react'
import { X, CheckCircle, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

export const DocumentDecisionModal = ({ isOpen, onClose, onConfirm, documentType = 'Document', initialDecision = 'Approve' }) => {
  const [decision, setDecision] = useState('Approved')
  const [reasonCategory, setReasonCategory] = useState('Wrong Document')
  const [comments, setComments] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setDecision(initialDecision === 'Approve' ? 'Approved' : 'Rejected')
      setReasonCategory('Wrong Document')
      setComments('')
    }
  }, [isOpen, initialDecision])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (decision === 'Rejected' && !comments.trim()) {
      toast.error('Comments are required for document rejection')
      return
    }

    setLoading(true)
    try {
      await onConfirm({
        decision,
        reasonCategory: decision === 'Rejected' ? reasonCategory : '',
        comments: comments.trim()
      })
      onClose()
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="w-full max-w-md rounded-2xl border border-border-custom bg-bg-surface p-6 shadow-2xl space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-custom pb-4">
          <div>
            <h3 className="text-sm font-bold text-txt-primary">Document Verification Decision</h3>
            <p className="text-[10px] text-txt-secondary mt-0.5">Reviewing: {documentType}</p>
          </div>
          <button 
            onClick={onClose} 
            className="rounded-lg p-1 text-txt-tertiary hover:bg-bg-page hover:text-txt-primary transition"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {/* Decision Selector Buttons */}
          <div className="space-y-2">
            <label className="block text-[10px] font-bold text-txt-secondary uppercase tracking-wider">
              Verification Decision
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDecision('Approved')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border text-xs font-semibold cursor-pointer transition-all ${
                  decision === 'Approved'
                    ? 'border-success-primary bg-success-bg/15 text-success-primary shadow-sm shadow-success-primary/10'
                    : 'border-border-custom bg-bg-page text-txt-secondary hover:text-txt-primary'
                }`}
              >
                <CheckCircle size={15} />
                Approve
              </button>
              <button
                type="button"
                onClick={() => setDecision('Rejected')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border text-xs font-semibold cursor-pointer transition-all ${
                  decision === 'Rejected'
                    ? 'border-danger-primary bg-danger-bg/15 text-danger-primary shadow-sm shadow-danger-primary/10'
                    : 'border-border-custom bg-bg-page text-txt-secondary hover:text-txt-primary'
                }`}
              >
                <AlertTriangle size={15} />
                Reject
              </button>
            </div>
          </div>

          {/* Reason Category - Only shown for Rejections */}
          {decision === 'Rejected' && (
            <div className="space-y-2 animate-slideDown">
              <label className="block text-[10px] font-bold text-txt-secondary uppercase tracking-wider">
                Reason Category *
              </label>
              <select
                value={reasonCategory}
                onChange={(e) => setReasonCategory(e.target.value)}
                className="w-full rounded-xl border border-border-custom bg-bg-page px-4 py-2.5 text-txt-primary focus:border-brand-indigo focus:outline-none transition"
              >
                <option value="Wrong Document">Wrong Document</option>
                <option value="Unreadable File">Unreadable File</option>
                <option value="Missing Information">Missing Information</option>
                <option value="Expired Document">Expired Document</option>
                <option value="Other">Other</option>
              </select>
            </div>
          )}

          {/* Comments Textarea */}
          <div className="space-y-2">
            <label className="block text-[10px] font-bold text-txt-secondary uppercase tracking-wider">
              {decision === 'Rejected' ? 'Rejection Comments *' : 'Approval Comments (Optional)'}
            </label>
            <textarea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              rows="3"
              required={decision === 'Rejected'}
              placeholder={
                decision === 'Rejected'
                  ? 'Please specify details on what is incorrect or missing...'
                  : 'Add notes about document completeness, validation date, etc.'
              }
              className="w-full rounded-xl border border-border-custom bg-bg-page px-4 py-2.5 text-txt-primary placeholder-txt-tertiary focus:border-brand-indigo focus:outline-none transition resize-none font-sans"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end pt-4 border-t border-border-custom mt-6">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border-custom bg-transparent px-5 py-2.5 font-semibold text-txt-secondary hover:bg-bg-page hover:text-txt-primary transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`rounded-xl px-5 py-2.5 font-semibold text-white shadow-md transition cursor-pointer flex items-center gap-1.5 ${
                decision === 'Approved'
                  ? 'bg-success-primary hover:bg-success-primary/90'
                  : 'bg-danger-primary hover:bg-danger-primary/90'
              }`}
            >
              {loading ? 'Submitting...' : 'Confirm Decision'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default DocumentDecisionModal
