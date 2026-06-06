import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// Base URL configuration
const isDevServer = window.location.port === '5173'
const baseURL = isDevServer ? '' : window.location.origin

const api = axios.create({
  baseURL,
  timeout: 60000, // 60s — generous timeout to accommodate CrewAI / LLM response times
})

// ── Simple in-memory GET cache (30s TTL) ──────────────────────────────────────
// Prevents re-fetching the same dashboard data when navigating between sidebar tabs.
const _cache = new Map() // key → { data, expiresAt }
const CACHE_TTL_MS = 30_000

const cacheKeyFor = (config) => {
  const params = config.params ? JSON.stringify(config.params) : ''
  return `${config.baseURL || ''}${config.url || ''}?${params}`
}

export const invalidateCache = (urlPattern) => {
  for (const key of _cache.keys()) {
    if (!urlPattern || key.includes(urlPattern)) _cache.delete(key)
  }
}

// Request interceptor — attach Bearer token + cache GET responses
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Check in-memory cache for GET requests
    if (config.method === 'get' || !config.method) {
      const cacheKey = cacheKeyFor(config)
      const cached = _cache.get(cacheKey)
      if (cached && Date.now() < cached.expiresAt) {
        // Return a resolved promise that looks like an axios response
        config.adapter = () => Promise.resolve({
          data: cached.data,
          status: 200,
          statusText: 'OK (cached)',
          headers: {},
          config,
        })
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor — cache GET results + handle 401s
api.interceptors.response.use(
  (response) => {
    const method = response.config.method
    if (method === 'get' || !method) {
      const cacheKey = cacheKeyFor(response.config)
      _cache.set(cacheKey, { data: response.data, expiresAt: Date.now() + CACHE_TTL_MS })
    }
    return response
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      useAuthStore.getState().logout()
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
