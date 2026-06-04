import React from 'react'
import { X, Download } from 'lucide-react'

export const DocumentViewerModal = ({ isOpen, onClose, url, filename }) => {
  if (!isOpen || !url) return null

  const isPDF = filename?.toLowerCase().endsWith('.pdf')
  const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(filename)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl h-[85vh] rounded-xl border border-border-custom bg-bg-surface flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-custom bg-bg-page">
          <div>
            <h3 className="text-sm font-bold text-txt-primary">Document Preview</h3>
            <p className="text-[10px] text-txt-secondary">{filename}</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={url}
              download={filename}
              className="p-1.5 rounded-lg border border-border-custom bg-bg-surface text-txt-secondary hover:text-txt-primary hover:border-brand-indigo/40 transition-all"
              title="Download File"
            >
              <Download size={16} />
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg border border-border-custom bg-bg-surface text-txt-secondary hover:text-txt-primary hover:border-brand-indigo/40 transition-all"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Preview Area */}
        <div className="flex-1 bg-bg-page flex items-center justify-center p-4 overflow-auto">
          {isPDF ? (
            <iframe
              src={url}
              className="w-full h-full rounded-lg border border-border-custom bg-white"
              title={filename}
            />
          ) : isImage ? (
            <img
              src={url}
              alt={filename}
              className="max-w-full max-h-full object-contain rounded-lg border border-border-custom shadow-md"
            />
          ) : (
            <div className="text-center space-y-4">
              <p className="text-sm text-txt-secondary">
                Preview not supported for this file type.
              </p>
              <a
                href={url}
                download={filename}
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand-indigo text-white rounded-lg text-xs font-semibold hover:bg-brand-indigo/90"
              >
                <Download size={14} />
                Download Document
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DocumentViewerModal
