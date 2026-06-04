import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Download, ShieldCheck, XCircle } from 'lucide-react'
import { EmptyState } from '../../components/ui/EmptyState'
import { StatusPill } from '../../components/ui/StatusPill'
import { decideProfileDocument, downloadProfileDocumentUrl, listReviewDocuments } from '../../api'

export const DocumentVerification = () => {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)

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

  const decide = async (doc, status) => {
    const rejection_comment = status === 'Rejected'
      ? window.prompt('Rejection comment') || ''
      : ''
    if (status === 'Rejected' && !rejection_comment.trim()) return
    try {
      await decideProfileDocument(doc.kind, doc.id, { status, rejection_comment })
      toast.success(`Document ${status.toLowerCase()}`)
      fetchData()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'Document review failed')
    }
  }

  return (
    <div className="rounded-xl border border-border-custom bg-bg-surface p-6 space-y-4">
      <div className="border-b border-border-custom pb-3">
        <h4 className="text-sm font-semibold">Document Verification</h4>
        <p className="text-[11px] text-txt-secondary">Review candidate and employee documents collected during profile setup and onboarding.</p>
      </div>

      {loading ? (
        <div className="text-xs text-txt-tertiary py-8">Loading uploaded documents...</div>
      ) : documents.length === 0 ? (
        <EmptyState title="No uploaded documents" description="Documents submitted by candidates and employees will appear here." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-bg-page text-txt-tertiary uppercase text-[10px]">
                <th className="py-2.5 px-3">Person</th>
                <th className="py-2.5 px-3">Document</th>
                <th className="py-2.5 px-3">Uploaded</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-custom/50">
              {documents.map((doc) => (
                <tr key={`${doc.kind}-${doc.id}`}>
                  <td className="py-3 px-3">
                    <span className="font-semibold block">{doc.username}</span>
                    <span className="text-[10px] text-txt-secondary capitalize">{doc.kind}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-semibold block">{doc.document_type}</span>
                    <span className="text-[10px] text-txt-secondary">{doc.original_filename}</span>
                    {doc.rejection_comment && <span className="text-[10px] text-danger-primary block mt-1">{doc.rejection_comment}</span>}
                  </td>
                  <td className="py-3 px-3 text-txt-secondary">{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '-'}</td>
                  <td className="py-3 px-3"><StatusPill status={doc.verification_status} /></td>
                  <td className="py-3 px-3 text-right space-x-2">
                    <a href={downloadProfileDocumentUrl(doc.kind, doc.id)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 px-2.5 py-1 border border-border-custom rounded-lg">
                      <Download size={12} />
                      Download
                    </a>
                    <button onClick={() => decide(doc, 'Approved')} className="inline-flex items-center gap-1 px-2.5 py-1 border border-success-primary/30 text-success-primary rounded-lg">
                      <ShieldCheck size={12} />
                      Approve
                    </button>
                    <button onClick={() => decide(doc, 'Rejected')} className="inline-flex items-center gap-1 px-2.5 py-1 border border-danger-primary/30 text-danger-primary rounded-lg">
                      <XCircle size={12} />
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default DocumentVerification
