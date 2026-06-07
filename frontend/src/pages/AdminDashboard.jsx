import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Users, FileText, BookOpen, Search, Shield, Save, Edit2, Trash2, RefreshCw, Plus, X, Power, Check, Info } from 'lucide-react'
import {
  getAdminUsers,
  updateAdminUser,
  getAdminPolicies,
  createAdminPolicy,
  updateAdminPolicy,
  deleteAdminPolicy,
  reindexAdminPolicy,
  getAdminKnowledge,
  createAdminKnowledge,
  updateAdminKnowledge,
  deleteAdminKnowledge,
  reindexAdminKnowledge
} from '../api'
import toast from 'react-hot-toast'

export const AdminDashboard = () => {
  const navigate = useNavigate()
  const location = useLocation()

  // Get active tab from URL search param
  const activeTab = new URLSearchParams(location.search).get('tab') || 'users'

  // States
  const [users, setUsers] = useState([])
  const [policies, setPolicies] = useState([])
  const [knowledge, setKnowledge] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  // Modal / Editor State
  const [editingDoc, setEditingDoc] = useState(null) // { id/filename, title, content, type: 'policy' | 'knowledge', category?: 'onboarding' | 'training' }
  const [isNewDoc, setIsNewDoc] = useState(false)
  const [syncingDocs, setSyncingDocs] = useState({}) // track re-indexing states by filename

  // Sync tab with navigation
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    if (!params.get('tab')) {
      navigate('/dashboard/admin?tab=users', { replace: true })
    }
  }, [location.search, navigate])

  // Fetch data depending on activeTab
  const loadData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'users') {
        const data = await getAdminUsers()
        setUsers(data)
      } else if (activeTab === 'policies') {
        const data = await getAdminPolicies()
        setPolicies(data)
      } else if (activeTab === 'knowledge') {
        const data = await getAdminKnowledge()
        setKnowledge(data)
      }
    } catch (err) {
      console.error('Failed to load admin data:', err)
      toast.error(err.response?.data?.detail || 'Failed to retrieve records')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [activeTab])

  // --- User management handlers ---
  const handleRoleChange = async (userId, newRole) => {
    try {
      const updated = await updateAdminUser(userId, { role: newRole })
      setUsers(users.map(u => u.id === userId ? updated : u))
      toast.success(`Role updated to ${newRole}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Role change failed')
    }
  }

  const handleStatusToggle = async (userId, currentStatus) => {
    try {
      const nextStatus = !currentStatus
      const updated = await updateAdminUser(userId, { is_active: nextStatus })
      setUsers(users.map(u => u.id === userId ? updated : u))
      toast.success(nextStatus ? 'User activated' : 'User deactivated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Status change failed')
    }
  }

  // --- Policy and Knowledge handlers ---
  const handleOpenEditor = (doc, isNew = false, type = 'policy') => {
    setIsNewDoc(isNew)
    if (isNew) {
      setEditingDoc({
        title: '',
        content: '',
        type,
        category: type === 'knowledge' ? 'onboarding' : undefined
      })
    } else {
      setEditingDoc({
        ...doc,
        type
      })
    }
  }

  const handleSaveDoc = async (e) => {
    e.preventDefault()
    if (!editingDoc.title.trim() || !editingDoc.content.trim()) {
      toast.error('Title and content are required')
      return
    }

    try {
      if (editingDoc.type === 'policy') {
        if (isNewDoc) {
          const res = await createAdminPolicy({
            title: editingDoc.title,
            content: editingDoc.content
          })
          setPolicies([res, ...policies])
          toast.success('Company policy created and synced to RAG!')
        } else {
          const res = await updateAdminPolicy(editingDoc.filename, {
            title: editingDoc.title,
            content: editingDoc.content
          })
          setPolicies(policies.map(p => p.filename === editingDoc.filename ? res : p))
          toast.success('Company policy updated and synced to RAG!')
        }
      } else {
        // Knowledge article
        if (isNewDoc) {
          const res = await createAdminKnowledge({
            title: editingDoc.title,
            category: editingDoc.category,
            content: editingDoc.content
          })
          setKnowledge([res, ...knowledge])
          toast.success('Knowledge article created and synced to RAG!')
        } else {
          const res = await updateAdminKnowledge(editingDoc.category, editingDoc.filename, {
            title: editingDoc.title,
            content: editingDoc.content
          })
          setKnowledge(knowledge.map(k => (k.filename === editingDoc.filename && k.category === editingDoc.category) ? res : k))
          toast.success('Knowledge article updated and synced to RAG!')
        }
      }
      setEditingDoc(null)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save document')
    }
  }

  const handleDeleteDoc = async (doc, type) => {
    const confirmMsg = `Are you sure you want to delete "${doc.title}"? This will permanently remove the document from the filesystem and Chroma RAG.`
    if (!window.confirm(confirmMsg)) return

    try {
      if (type === 'policy') {
        await deleteAdminPolicy(doc.filename)
        setPolicies(policies.filter(p => p.filename !== doc.filename))
        toast.success('Policy deleted and removed from RAG!')
      } else {
        await deleteAdminKnowledge(doc.category, doc.filename)
        setKnowledge(knowledge.filter(k => !(k.filename === doc.filename && k.category === doc.category)))
        toast.success('Knowledge article deleted and removed from RAG!')
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete document')
    }
  }

  const handleReindexDoc = async (doc, type) => {
    const idKey = type === 'policy' ? doc.filename : `${doc.category}/${doc.filename}`
    setSyncingDocs(prev => ({ ...prev, [idKey]: true }))
    try {
      if (type === 'policy') {
        await reindexAdminPolicy(doc.filename)
      } else {
        await reindexAdminKnowledge(doc.category, doc.filename)
      }
      toast.success('Index sync completed successfully!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to synchronize with Chroma RAG')
    } finally {
      setSyncingDocs(prev => ({ ...prev, [idKey]: false }))
    }
  }

  // Filter lists
  const filteredUsers = users.filter(u =>
    u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.role.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredPolicies = policies.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.content.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredKnowledge = knowledge.filter(k =>
    k.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    k.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    k.category.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-8 text-txt-primary">
      {/* Header Banner */}
      <div className="flex items-center justify-between border-b border-border-custom pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Admin Operations Console</h2>
          <p className="text-xs text-txt-secondary mt-1">
            Manage user roles, platform access settings, and company knowledge base contents.
          </p>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="flex space-x-1 border-b border-border-custom pb-0.5">
        {[
          { id: 'users', label: 'User Management', icon: Users },
          { id: 'policies', label: 'Company Policies', icon: FileText },
          { id: 'knowledge', label: 'Employee Knowledge', icon: BookOpen }
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => {
                setSearchQuery('')
                navigate(`/dashboard/admin?tab=${tab.id}`)
              }}
              className={`flex items-center space-x-2 px-4 py-2 border-b-2 text-xs font-semibold cursor-pointer transition-all ${
                isActive
                  ? 'border-brand-indigo text-brand-indigo'
                  : 'border-transparent text-txt-secondary hover:text-txt-primary'
              }`}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Main Grid View */}
      <div className="space-y-6">
        {/* Search and Action Bar */}
        <div className="flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <input
              type="text"
              placeholder={
                activeTab === 'users'
                  ? 'Search users by username...'
                  : activeTab === 'policies'
                  ? 'Search policies by title...'
                  : 'Search knowledge articles...'
              }
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-bg-surface border border-border-custom text-xs outline-none px-3 py-2 pl-9 rounded-lg text-txt-primary focus:border-brand-indigo transition-colors"
            />
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-txt-tertiary" />
          </div>

          {activeTab === 'policies' && (
            <button
              onClick={() => handleOpenEditor(null, true, 'policy')}
              className="bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center space-x-1.5 cursor-pointer active:scale-98 transition-all"
            >
              <Plus size={14} />
              <span>New Policy</span>
            </button>
          )}

          {activeTab === 'knowledge' && (
            <button
              onClick={() => handleOpenEditor(null, true, 'knowledge')}
              className="bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center space-x-1.5 cursor-pointer active:scale-98 transition-all"
            >
              <Plus size={14} />
              <span>New Article</span>
            </button>
          )}
        </div>

        {/* LOADING INDICATOR */}
        {loading ? (
          <div className="flex items-center justify-center py-16 bg-bg-surface border border-border-custom rounded-xl">
            <div className="flex flex-col items-center gap-2">
              <div className="w-6 h-6 rounded-full border-2 border-brand-indigo border-t-transparent animate-spin" />
              <p className="text-txt-tertiary text-[11px]">Loading records...</p>
            </div>
          </div>
        ) : (
          <div className="bg-bg-surface border border-border-custom rounded-xl overflow-hidden shadow-xs">
            {/* TABS BODY */}
            {activeTab === 'users' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-bg-page text-txt-secondary font-bold uppercase tracking-wider border-b border-border-custom">
                      <th className="py-3 px-4">User ID</th>
                      <th className="py-3 px-4">Username</th>
                      <th className="py-3 px-4">Current Role</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-custom/50">
                    {filteredUsers.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="py-12 text-center text-txt-tertiary">
                          No users found matching search query.
                        </td>
                      </tr>
                    ) : (
                      filteredUsers.map((u) => (
                        <tr key={u.id} className="hover:bg-bg-page/40 transition-colors">
                          <td className="py-3.5 px-4 font-mono text-txt-tertiary">#{u.id}</td>
                          <td className="py-3.5 px-4 font-semibold">{u.username}</td>
                          <td className="py-3.5 px-4">
                            <select
                              value={u.role}
                              onChange={(e) => handleRoleChange(u.id, e.target.value)}
                              className="bg-bg-page border border-border-custom text-xs px-2.5 py-1.5 rounded-lg outline-none focus:border-brand-indigo text-txt-primary cursor-pointer font-medium"
                            >
                              {Array.from(USER_ROLES).map((r) => (
                                <option key={r} value={r}>
                                  {r.toUpperCase()}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                u.is_active
                                  ? 'bg-success-bg text-success-primary border-success-primary/25'
                                  : 'bg-danger-bg text-danger-primary border-danger-primary/25'
                              }`}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-success-primary' : 'bg-danger-primary'}`} />
                              {u.is_active ? 'Active' : 'Deactivated'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => handleStatusToggle(u.id, u.is_active)}
                              className={`inline-flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer transition-colors ${
                                u.is_active
                                  ? 'border-danger-primary/20 bg-danger-bg/10 hover:bg-danger-bg text-danger-primary'
                                  : 'border-success-primary/20 bg-success-bg/10 hover:bg-success-bg text-success-primary'
                              }`}
                            >
                              <Power size={11} />
                              <span>{u.is_active ? 'Deactivate' : 'Activate'}</span>
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'policies' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-bg-page text-txt-secondary font-bold uppercase tracking-wider border-b border-border-custom">
                      <th className="py-3 px-4">Policy Title</th>
                      <th className="py-3 px-4">Filename</th>
                      <th className="py-3 px-4">Content Preview</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-custom/50">
                    {filteredPolicies.length === 0 ? (
                      <tr>
                        <td colSpan="4" className="py-12 text-center text-txt-tertiary">
                          No company policies registered.
                        </td>
                      </tr>
                    ) : (
                      filteredPolicies.map((p) => {
                        const isSyncing = syncingDocs[p.filename]
                        return (
                          <tr key={p.filename} className="hover:bg-bg-page/40 transition-colors">
                            <td className="py-3.5 px-4 font-semibold text-txt-primary">{p.title}</td>
                            <td className="py-3.5 px-4 font-mono text-txt-tertiary text-[11px]">{p.filename}</td>
                            <td className="py-3.5 px-4 text-txt-secondary truncate max-w-xs">{p.content}</td>
                            <td className="py-3.5 px-4 text-right space-x-1.5">
                              <button
                                onClick={() => handleReindexDoc(p, 'policy')}
                                disabled={isSyncing}
                                title="Re-sync policy content into Chroma RAG"
                                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated text-txt-secondary hover:text-brand-indigo cursor-pointer transition-colors disabled:opacity-40"
                              >
                                <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
                              </button>
                              <button
                                onClick={() => handleOpenEditor(p, false, 'policy')}
                                title="Edit policy text"
                                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated text-txt-secondary hover:text-brand-indigo cursor-pointer transition-colors"
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                onClick={() => handleDeleteDoc(p, 'policy')}
                                title="Delete policy permanently"
                                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-danger-bg/40 text-txt-secondary hover:text-danger-primary cursor-pointer transition-colors"
                              >
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'knowledge' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-bg-page text-txt-secondary font-bold uppercase tracking-wider border-b border-border-custom">
                      <th className="py-3 px-4">Article Title</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Filename</th>
                      <th className="py-3 px-4">Content Preview</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-custom/50">
                    {filteredKnowledge.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="py-12 text-center text-txt-tertiary">
                          No knowledge articles found.
                        </td>
                      </tr>
                    ) : (
                      filteredKnowledge.map((k) => {
                        const idKey = `${k.category}/${k.filename}`
                        const isSyncing = syncingDocs[idKey]
                        return (
                          <tr key={idKey} className="hover:bg-bg-page/40 transition-colors">
                            <td className="py-3.5 px-4 font-semibold text-txt-primary">{k.title}</td>
                            <td className="py-3.5 px-4">
                              <span className="text-[10px] font-bold text-brand-indigo bg-brand-indigo-muted border border-brand-indigo/15 px-2 py-0.5 rounded-full uppercase">
                                {k.category}
                              </span>
                            </td>
                            <td className="py-3.5 px-4 font-mono text-txt-tertiary text-[11px]">{k.filename}</td>
                            <td className="py-3.5 px-4 text-txt-secondary truncate max-w-xs">{k.content}</td>
                            <td className="py-3.5 px-4 text-right space-x-1.5">
                              <button
                                onClick={() => handleReindexDoc(k, 'knowledge')}
                                disabled={isSyncing}
                                title="Re-sync article content into Chroma RAG"
                                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated text-txt-secondary hover:text-brand-indigo cursor-pointer transition-colors disabled:opacity-40"
                              >
                                <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
                              </button>
                              <button
                                onClick={() => handleOpenEditor(k, false, 'knowledge')}
                                title="Edit article text"
                                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-bg-elevated text-txt-secondary hover:text-brand-indigo cursor-pointer transition-colors"
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                onClick={() => handleDeleteDoc(k, 'knowledge')}
                                title="Delete article permanently"
                                className="p-1.5 rounded-lg border border-border-custom bg-bg-page hover:bg-danger-bg/40 text-txt-secondary hover:text-danger-primary cursor-pointer transition-colors"
                              >
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* DOCUMENT CREATE/EDIT MODAL OVERLAY */}
      <AnimatePresence>
        {editingDoc && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setEditingDoc(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-xs"
            />

            {/* Modal Dialog */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="relative w-full max-w-2xl bg-bg-surface border border-border-custom rounded-xl shadow-xl overflow-hidden flex flex-col text-xs"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-border-custom p-4 bg-bg-page/40">
                <div>
                  <h4 className="text-sm font-bold">
                    {isNewDoc
                      ? `Create New ${editingDoc.type === 'policy' ? 'Policy' : 'Knowledge Article'}`
                      : `Edit ${editingDoc.type === 'policy' ? 'Policy' : 'Knowledge Article'}`}
                  </h4>
                  <p className="text-[10px] text-txt-secondary mt-0.5">
                    Modifying this file will automatically trigger immediate vector sync for AI Copilots.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setEditingDoc(null)}
                  className="p-1 text-txt-tertiary hover:text-txt-primary hover:bg-bg-page/80 rounded-lg cursor-pointer transition-colors"
                >
                  <X size={15} />
                </button>
              </div>

              {/* Form Body */}
              <form onSubmit={handleSaveDoc} className="p-6 space-y-4 flex-1 overflow-y-auto">
                <div className="grid grid-cols-1 gap-4">
                  {/* Category selector for knowledge */}
                  {editingDoc.type === 'knowledge' && (
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-txt-secondary uppercase">
                        Knowledge Category
                      </label>
                      <select
                        disabled={!isNewDoc}
                        value={editingDoc.category}
                        onChange={(e) => setEditingDoc({ ...editingDoc, category: e.target.value })}
                        className="w-full bg-bg-page border border-border-custom text-xs p-2 rounded-lg outline-none focus:border-brand-indigo text-txt-primary cursor-pointer disabled:opacity-40"
                      >
                        <option value="onboarding">Onboarding Guides</option>
                        <option value="training">Training Best Practices</option>
                      </select>
                    </div>
                  )}

                  {/* Document Title */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-txt-secondary uppercase">Title</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Remote Work Policy"
                      value={editingDoc.title}
                      onChange={(e) => setEditingDoc({ ...editingDoc, title: e.target.value })}
                      className="w-full bg-bg-page border border-border-custom text-xs p-2 rounded-lg outline-none focus:border-brand-indigo text-txt-primary"
                    />
                  </div>

                  {/* Document Content */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-txt-secondary uppercase">Content</label>
                    <textarea
                      required
                      rows={12}
                      placeholder="Enter detailed Markdown/Text contents here..."
                      value={editingDoc.content}
                      onChange={(e) => setEditingDoc({ ...editingDoc, content: e.target.value })}
                      className="w-full bg-bg-page border border-border-custom text-xs p-3 rounded-lg outline-none focus:border-brand-indigo text-txt-primary font-mono leading-relaxed"
                    />
                  </div>
                </div>

                {/* Footer Buttons */}
                <div className="flex justify-end space-x-2 pt-4 border-t border-border-custom/50">
                  <button
                    type="button"
                    onClick={() => setEditingDoc(null)}
                    className="px-4 py-2 rounded-lg border border-border-custom hover:bg-bg-page text-xs font-semibold cursor-pointer text-txt-secondary transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-brand-indigo hover:bg-brand-indigo-hover text-white text-xs font-semibold flex items-center space-x-1.5 cursor-pointer active:scale-98 transition-all"
                  >
                    <Save size={13} />
                    <span>Save & Ingest</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default AdminDashboard
