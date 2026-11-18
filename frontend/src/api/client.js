import axios from 'axios'

const API_BASE_URL = typeof import.meta.env.VITE_API_URL === 'string' && import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : (import.meta.env.PROD ? 'https://budgetbuddy-app-six.vercel.app/api' : 'http://127.0.0.1:8000/api')

export const TOKEN_KEYS = {
  access: 'budgetbuddy.access',
  refresh: 'budgetbuddy.refresh',
}

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

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
    const refresh = localStorage.getItem(TOKEN_KEYS.refresh)

    if (error.response?.status === 401 && original && !original._retried && refresh) {
      original._retried = true
      try {
        const { data } = await api.post('/auth/refresh/', { refresh }, { withCredentials: true })
        if (data.access) {
          localStorage.setItem(TOKEN_KEYS.access, data.access)
          original.headers.Authorization = `Bearer ${data.access}`
        }
        if (data.refresh) {
          localStorage.setItem(TOKEN_KEYS.refresh, data.refresh)
        }
        return api(original)
      } catch (refreshErr) {
        localStorage.removeItem(TOKEN_KEYS.access)
        localStorage.removeItem(TOKEN_KEYS.refresh)
        throw refreshErr
      }
    }
    return Promise.reject(error)
  },
)

export default api
