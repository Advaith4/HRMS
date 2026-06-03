import { create } from 'zustand'
import { decodeJwt } from '../utils/jwt'

const getInitialState = () => {
  const token = localStorage.getItem('tf_token')
  const hasResume = localStorage.getItem('tf_has_resume') === 'true'
  if (token) {
    const decoded = decodeJwt(token)
    if (decoded) {
      // Check token expiration (if 'exp' is present)
      const isExpired = decoded.exp ? decoded.exp * 1000 < Date.now() : false
      if (!isExpired) {
        return {
          token,
          user: {
            id: decoded.sub || decoded.user_id,
            username: decoded.username,
            role: decoded.role,
          },
          role: decoded.role || 'candidate',
          hasResume,
          isAuthenticated: true,
        }
      }
    }
  }
  return {
    token: null,
    user: null,
    role: null,
    hasResume: false,
    isAuthenticated: false,
  }
}

export const useAuthStore = create((set) => ({
  ...getInitialState(),

  setAuth: (token, hasResumeVal) => {
    localStorage.setItem('tf_token', token)
    localStorage.setItem('tf_has_resume', String(!!hasResumeVal))
    const decoded = decodeJwt(token)
    
    set({
      token,
      user: decoded ? {
        id: decoded.sub || decoded.user_id,
        username: decoded.username,
        role: decoded.role,
      } : null,
      role: decoded?.role || 'candidate',
      hasResume: !!hasResumeVal,
      isAuthenticated: !!token,
    })
  },

  updateHasResume: (val) => {
    localStorage.setItem('tf_has_resume', String(!!val))
    set({ hasResume: !!val })
  },

  logout: () => {
    localStorage.removeItem('tf_token')
    localStorage.removeItem('tf_has_resume')
    set({
      token: null,
      user: null,
      role: null,
      hasResume: false,
      isAuthenticated: false,
    })
  }
}))
