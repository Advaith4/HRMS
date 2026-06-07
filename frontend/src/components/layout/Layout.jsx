import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useLayoutStore } from '../../store/layoutStore'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { motion, AnimatePresence } from 'framer-motion'

export const Layout = () => {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  
  const isFullscreen = useLayoutStore(state => state.isFullscreen)
  const isInterviewRoute = isFullscreen

  // Protect routes - redirect to /login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen min-h-0 overflow-hidden bg-bg-page select-text">
      {/* Sidebar Navigation */}
      {!isInterviewRoute && <Sidebar />}

      {/* Main Container */}
      <div className={`flex-1 flex flex-col min-w-0 min-h-0 ${isInterviewRoute ? 'pb-0' : 'pb-16 md:pb-0'}`}>
        {/* Top Header */}
        {!isInterviewRoute && <TopBar />}

        {/* Dynamic Content Frame */}
        <main className={`flex-1 min-h-0 w-full ${isInterviewRoute ? 'overflow-hidden p-0 max-w-none h-full' : 'overflow-y-auto p-4 sm:p-6 md:p-8 max-w-7xl mx-auto'}`}>
          <AnimatePresence mode="wait">
            <motion.div
              className={isInterviewRoute ? 'h-full min-h-0' : undefined}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
export default Layout
