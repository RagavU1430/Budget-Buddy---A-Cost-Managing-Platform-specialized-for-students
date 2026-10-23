import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export const TOKEN_KEYS = {
  access: 'budgetbuddy.access',
  refresh: 'budgetbuddy.refresh',
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
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
        const { data } = await axios.post(`${API_BASE_URL}/api/auth/refresh/`, { refresh })
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
