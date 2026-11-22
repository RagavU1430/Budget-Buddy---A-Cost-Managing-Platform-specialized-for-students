import axios from 'axios'

const API_BASE_URL = typeof import.meta.env.VITE_API_URL === 'string' && import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : '/api'

// Only access token in localStorage (short-lived, 60 min)
// Refresh token is stored in httpOnly cookie by backend
export const TOKEN_KEYS = {
  access: 'budgetbuddy.access',
  // refresh: 'budgetbuddy.refresh', // DEPRECATED - now httpOnly cookie
}

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Required for httpOnly cookies
  headers: { 'Content-Type': 'application/json' },
})

// Promise to prevent multiple simultaneous refresh attempts
let refreshPromise = null

api.interceptors.request.use((config) => {
  // Prevent double /api/ prefix if already present in baseURL
  if (config.url && config.url.startsWith('/api/')) {
    config.url = config.url.replace('/api/', '/')
  }
  const access = localStorage.getItem(TOKEN_KEYS.access)
  if (
    access &&
    !config.url?.includes('/auth/refresh') &&
    !config.url?.includes('/auth/login') &&
    !config.url?.includes('/auth/register')
  ) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true

      // Use shared promise to prevent multiple simultaneous refresh attempts
      if (!refreshPromise) {
        refreshPromise = (async () => {
          try {
            // Backend reads refresh token from httpOnly cookie automatically
            const { data } = await api.post('/auth/refresh/', {}, { withCredentials: true })
            if (data.access) {
              localStorage.setItem(TOKEN_KEYS.access, data.access)
              original.headers.Authorization = `Bearer ${data.access}`
            }
            // New refresh token is set via httpOnly cookie by backend
            return data
          } catch (refreshErr) {
            localStorage.removeItem(TOKEN_KEYS.access)
            throw refreshErr
          } finally {
            refreshPromise = null
          }
        })()
      }

      try {
        await refreshPromise
        return api(original)
      } catch (refreshErr) {
        throw refreshErr
      }
    }
    return Promise.reject(error)
  },
)

export default api
