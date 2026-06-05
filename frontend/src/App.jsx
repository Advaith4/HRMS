import React, { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import { Layout } from './components/layout/Layout'

// Lazy-load page components – each becomes a separate async chunk
// They only download when the user first navigates to that route
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })))
const HRDashboard = lazy(() => import('./pages/HRDashboard').then(m => ({ default: m.HRDashboard })))
const CandidateDashboard = lazy(() => import('./pages/CandidateDashboard').then(m => ({ default: m.CandidateDashboard })))
const ManagerDashboard = lazy(() => import('./pages/ManagerDashboard').then(m => ({ default: m.ManagerDashboard })))
const EmployeeDashboard = lazy(() => import('./pages/EmployeeDashboard').then(m => ({ default: m.EmployeeDashboard })))
const InterviewPage = lazy(() => import('./pages/interview/InterviewPage').then(m => ({ default: m.default })))
const MockInterviewPage = lazy(() => import('./pages/interview/MockInterviewPage').then(m => ({ default: m.default })))
const InterviewReports = lazy(() => import('./pages/hr/InterviewReports').then(m => ({ default: m.InterviewReports })))

// Minimal loading fallback shown while a chunk downloads
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-bg-page">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 rounded-full border-2 border-brand-indigo border-t-transparent animate-spin" />
      <p className="text-txt-tertiary text-sm">Loading…</p>
    </div>
  </div>
)

// Root redirect handler based on user role
const RootRedirect = () => {
  const { isAuthenticated, role } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Redirect to role dashboard
  const normRole = (role || '').toLowerCase()
  if (normRole === 'hr' || normRole === 'admin') {
    return <Navigate to="/dashboard/hr" replace />
  }
  if (normRole === 'manager') {
    return <Navigate to="/dashboard/manager" replace />
  }
  if (normRole === 'employee') {
    return <Navigate to="/dashboard/employee" replace />
  }
  return <Navigate to="/dashboard/candidate" replace />
}

const RoleGuard = ({ allowedRoles, children }) => {
  const { isAuthenticated, role } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const normRole = (role || '').toLowerCase()
  if (!allowedRoles.includes(normRole)) {
    // Redirect to their default dashboard if not allowed
    if (normRole === 'hr' || normRole === 'admin') {
      return <Navigate to="/dashboard/hr" replace />
    }
    if (normRole === 'manager') {
      return <Navigate to="/dashboard/manager" replace />
    }
    if (normRole === 'employee') {
      return <Navigate to="/dashboard/employee" replace />
    }
    return <Navigate to="/dashboard/candidate" replace />
  }

  return children
}

export const App = () => {
  return (
    <BrowserRouter>
      {/* Toast Notification Container with Dark Spec Custom Colors */}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1A2236',
            color: '#F1F5F9',
            border: '1px solid #2A3F5F',
            fontSize: '13px',
            fontFamily: 'Inter, system-ui, sans-serif'
          },
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#1A2236'
            }
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#1A2236'
            }
          }
        }}
      />

      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Auth Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Dashboard Layout Routes */}
          <Route element={<Layout />}>
            {/* Dashboards */}
            <Route path="/dashboard/hr" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard /></RoleGuard>} />
            <Route path="/dashboard/manager" element={<RoleGuard allowedRoles={['manager']}><ManagerDashboard /></RoleGuard>} />
            <Route path="/dashboard/candidate" element={<RoleGuard allowedRoles={['candidate']}><CandidateDashboard /></RoleGuard>} />
            <Route path="/dashboard/employee" element={<RoleGuard allowedRoles={['employee']}><EmployeeDashboard /></RoleGuard>} />

            {/* HR Sub routes */}
            <Route path="/hr/jobs" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="jobs" /></RoleGuard>} />
            <Route path="/hr/pipeline" element={<RoleGuard allowedRoles={['hr', 'admin', 'manager']}><HRDashboard activeTab="pipeline" /></RoleGuard>} />
            <Route path="/hr/candidates" element={<RoleGuard allowedRoles={['hr', 'admin', 'manager']}><HRDashboard activeTab="candidates" /></RoleGuard>} />
            <Route path="/hr/leaves" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="leaves" /></RoleGuard>} />
            <Route path="/hr/directory" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="directory" /></RoleGuard>} />
            <Route path="/hr/departments" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="departments" /></RoleGuard>} />
            <Route path="/hr/designations" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="designations" /></RoleGuard>} />
            <Route path="/hr/tickets" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="tickets" /></RoleGuard>} />
            <Route path="/hr/promotions" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="promotions" /></RoleGuard>} />
            <Route path="/hr/intelligence" element={<RoleGuard allowedRoles={['hr', 'admin', 'manager']}><InterviewReports /></RoleGuard>} />
            <Route path="/hr/onboarding" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="onboarding" /></RoleGuard>} />
            <Route path="/hr/training" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="training" /></RoleGuard>} />
            <Route path="/hr/documents" element={<RoleGuard allowedRoles={['hr', 'admin']}><HRDashboard activeTab="documents" /></RoleGuard>} />

            {/* Manager Sub routes */}
            <Route path="/manager/leaves" element={<RoleGuard allowedRoles={['manager']}><ManagerDashboard activeTab="leaves" /></RoleGuard>} />
            <Route path="/manager/training" element={<RoleGuard allowedRoles={['manager']}><ManagerDashboard activeTab="training" /></RoleGuard>} />

            {/* Candidate Sub routes */}
            <Route path="/jobs" element={<RoleGuard allowedRoles={['candidate']}><CandidateDashboard activeTab="jobs" /></RoleGuard>} />
            <Route path="/applications" element={<RoleGuard allowedRoles={['candidate']}><CandidateDashboard activeTab="applications" /></RoleGuard>} />

            {/* Interview Routes */}
            <Route path="/interview" element={<RoleGuard allowedRoles={['candidate']}><InterviewPage /></RoleGuard>} />
            <Route path="/mock-interview" element={<RoleGuard allowedRoles={['candidate']}><MockInterviewPage /></RoleGuard>} />
          </Route>

          {/* Catch-all root redirect */}
          <Route path="/" element={<RootRedirect />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>

    </BrowserRouter>
  )
}
export default App
