import axios from 'axios'

const API_BASE_URL = typeof import.meta.env.VITE_API_URL === 'string' && import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : (import.meta.env.PROD ? 'https://budgetbuddy-student.vercel.app' : 'http://127.0.0.1:8000')

export const TOKEN_KEYS = {
  access: 'budgetbuddy.access',
  refresh: 'budgetbuddy.refresh',
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  // Prevent double /api/ prefix if already present in baseURL
  if (config.url && config.url.startsWith('/api/')) {
    config.url = config.url.replace('/api/', '/')
  }
  const access = localStorage.getItem(TOKEN_KEYS.access)
  if (access) {
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
        const { data } = await api.post('/auth/refresh/', { refresh })
        localStorage.setItem(TOKEN_KEYS.access, data.access)
        if (data.refresh) {
          localStorage.setItem(TOKEN_KEYS.refresh, data.refresh)
        }
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch {
        localStorage.removeItem(TOKEN_KEYS.access)
        localStorage.removeItem(TOKEN_KEYS.refresh)
      }
    }
    return Promise.reject(error)
  },
)

export default api
