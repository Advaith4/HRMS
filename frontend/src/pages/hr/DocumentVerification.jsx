import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Download, ShieldCheck, XCircle, Eye, ChevronDown, ChevronUp, FileText } from 'lucide-react'
import { EmptyState } from '../../components/ui/EmptyState'
import { StatusPill } from '../../components/ui/StatusPill'
import { decideProfileDocument, downloadProfileDocumentUrl, listReviewDocuments } from '../../api'
import api from '../../api/axios'
import DocumentViewerModal from '../../components/DocumentViewerModal'

export const DocumentVerification = () => {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState({
    Identity: true,
    Education: true,
    Employment: true,
    Other: true
  })
  
  // Preview states
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewUrl, setPreviewUrl] = useState('')
  const [previewFilename, setPreviewFilename] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      setDocuments(await listReviewDocuments())
    } catch (err) {
      console.error(err)
      toast.error('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const toggleAccordion = (sec) => {
    setExpanded(prev => ({ ...prev, [sec]: !prev[sec] }))
  }

  const handlePreview = async (doc) => {
    const loadingToast = toast.loading('Loading preview...')
    try {
      const response = await api.get(`/api/profile/documents/${doc.kind}/${doc.id}/download`, {
        responseType: 'blob'
      })
      const file = new Blob([response.data], { type: response.headers['content-type'] })
      const fileURL = URL.createObjectURL(file)
      
      setPreviewUrl(fileURL)
      setPreviewFilename(doc.original_filename)
      setPreviewOpen(true)
      toast.dismiss(loadingToast)
    } catch (err) {
      console.error(err)
      toast.dismiss(loadingToast)
      toast.error('Could not load document preview')
    }
  }

  const decide = async (doc, status) => {
    let rejection_comment = ''
    if (status === 'Rejected') {
      rejection_comment = window.prompt('Please enter the reason for rejection (required):')
      if (rejection_comment === null) return // user cancelled
      if (!rejection_comment.trim()) {
        toast.error('Rejection reason is required')
        return
      }
    }
    try {
      await decideProfileDocument(doc.kind, doc.id, { status, rejection_comment: rejection_comment || '' })
      toast.success(`Document ${status.toLowerCase()}`)
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Document review failed')
    }
  }

  // Categorize document types into accordion groups
  const categorizeDocument = (docType) => {
    const t = docType?.toLowerCase() || ''
    if (t.includes('id') || t.includes('passport') || t.includes('aadhaar') || t.includes('pan') || t.includes('license') || t.includes('identity')) {
      return 'Identity'
    }
    if (t.includes('academic') || t.includes('education') || t.includes('degree') || t.includes('certificate') || t.includes('marklist') || t.includes('transcript')) {
      return 'Education'
    }
    if (t.includes('resume') || t.includes('experience') || t.includes('offer') || t.includes('payslip') || t.includes('relieving') || t.includes('letter') || t.includes('employment')) {
      return 'Employment'
    }
    return 'Other'
  }

  // Grouped documents object
  const grouped = {
    Identity: [],
    Education: [],
    Employment: [],
    Other: []
  }

  documents.forEach(doc => {
    const cat = categorizeDocument(doc.document_type)
    grouped[cat].push(doc)
  })

  return (
    <div className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-6">
      <div className="border-b border-border-custom pb-3 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold">Document Verification Pipeline</h4>
          <p className="text-[11px] text-txt-secondary">Review, preview, and approve employee/candidate documents under relevant folders.</p>
        </div>
        <span className="text-[10px] bg-brand-indigo/15 text-brand-indigo px-2 py-0.5 rounded-full font-bold">
          {documents.filter(d => d.verification_status === 'Pending Review').length} Pending Review
        </span>
      </div>

      {loading ? (
        <div className="text-xs text-txt-tertiary py-8 text-center">Loading uploaded documents...</div>
      ) : documents.length === 0 ? (
        <EmptyState title="No uploaded documents" description="Documents submitted by candidates and employees will appear here." />
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([category, items]) => {
            if (items.length === 0) return null
            const isExpanded = expanded[category]
            const pendingCount = items.filter(d => d.verification_status === 'Pending Review').length

            return (
              <div key={category} className="border border-border-custom rounded-xl overflow-hidden bg-bg-page/40">
                {/* Accordion Header */}
                <button
                  onClick={() => toggleAccordion(category)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-bg-page hover:bg-bg-page/80 border-b border-border-custom transition-all text-xs font-bold"
                >
                  <div className="flex items-center gap-2">
                    <FileText size={14} className="text-brand-indigo" />
                    <span>{category} Folder ({items.length})</span>
                    {pendingCount > 0 && (
                      <span className="bg-warning-bg/40 text-warning-primary text-[9px] px-1.5 py-0.5 rounded font-semibold ml-2">
                        {pendingCount} Pending
                      </span>
                    )}
                  </div>
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {/* Accordion Table Content */}
                {isExpanded && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-bg-page/80 text-txt-tertiary uppercase text-[9px]">
                          <th className="py-2.5 px-4">User</th>
                          <th className="py-2.5 px-4">Document Type & File</th>
                          <th className="py-2.5 px-4">Submitted Date</th>
                          <th className="py-2.5 px-4">Status</th>
                          <th className="py-2.5 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-custom/50">
                        {items.map((doc) => (
                          <tr key={`${doc.kind}-${doc.id}`} className="hover:bg-bg-page/10">
                            <td className="py-3 px-4">
                              <span className="font-semibold block">{doc.username}</span>
                              <span className="text-[10px] text-txt-secondary capitalize">{doc.kind}</span>
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-semibold block">{doc.document_type}</span>
                              <span className="text-[10px] text-txt-secondary">{doc.original_filename}</span>
                              {doc.rejection_comment && (
                                <span className="text-[10px] text-red-400 block mt-1">
                                  <strong>Reason:</strong> {doc.rejection_comment}
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-txt-secondary">
                              {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '-'}
                            </td>
                            <td className="py-3 px-4">
                              <StatusPill status={doc.verification_status} />
                            </td>
                            <td className="py-3 px-4 text-right space-x-1.5">
                              <button
                                onClick={() => handlePreview(doc)}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-border-custom bg-bg-surface hover:text-brand-indigo hover:border-brand-indigo/40 rounded-lg text-[10px] font-semibold transition-all"
                              >
                                <Eye size={12} />
                                Preview
                              </button>
                              <a
                                href={downloadProfileDocumentUrl(doc.kind, doc.id)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-border-custom bg-bg-surface hover:text-txt-primary rounded-lg text-[10px] font-semibold transition-all"
                              >
                                <Download size={12} />
                                Download
                              </a>
                              {doc.verification_status !== 'Approved' && (
                                <button
                                  onClick={() => decide(doc, 'Approved')}
                                  className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-success-primary/20 text-success-primary bg-success-bg/10 hover:bg-success-bg/25 rounded-lg text-[10px] font-semibold transition-all"
                                >
                                  <ShieldCheck size={12} />
                                  Approve
                                </button>
                              )}
                              {doc.verification_status !== 'Rejected' && (
                                <button
                                  onClick={() => decide(doc, 'Rejected')}
                                  className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-danger-primary/20 text-danger-primary bg-danger-bg/10 hover:bg-danger-bg/25 rounded-lg text-[10px] font-semibold transition-all"
                                >
                                  <XCircle size={12} />
                                  Reject
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Document Preview Modal */}
      <DocumentViewerModal
        isOpen={previewOpen}
        onClose={() => {
          setPreviewOpen(false)
          URL.revokeObjectURL(previewUrl)
          setPreviewUrl('')
        }}
        url={previewUrl}
        filename={previewFilename}
      />
    </div>
  )
}

export default DocumentVerification
