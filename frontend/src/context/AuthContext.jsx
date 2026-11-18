import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import api, { TOKEN_KEYS } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const storeTokens = useCallback((data) => {
    if (data?.access) localStorage.setItem(TOKEN_KEYS.access, data.access)
    if (data?.refresh) localStorage.setItem(TOKEN_KEYS.refresh, data.refresh)
  }, [])

  const clearTokens = useCallback(() => {
    localStorage.removeItem(TOKEN_KEYS.access)
    localStorage.removeItem(TOKEN_KEYS.refresh)
  }, [])

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me/')
      setUser(data)
      return data
    } catch {
      clearTokens()
      setUser(null)
      throw new Error('Not authenticated')
    }
  }, [clearTokens])

  const login = useCallback(
    async ({ email, password }) => {
      const { data } = await api.post('/auth/login/', { email, password })
      storeTokens(data)
      setUser(data.user)
      return data.user
    },
    [storeTokens],
  )

  const register = useCallback(
    async (payload) => {
      const { data } = await api.post('/auth/register/', payload)
      storeTokens(data)
      setUser(data.user)
      return data.user
    },
    [storeTokens],
  )

  const logout = useCallback(async () => {
    try {
      const refresh = localStorage.getItem(TOKEN_KEYS.refresh)
      await api.post('/auth/logout/', { refresh })
    } catch {
      // Ignore logout errors
    } finally {
      clearTokens()
      setUser(null)
      window.dispatchEvent(new Event('budgetbuddy:data-refresh'))
    }
  }, [clearTokens])

  const updateProfile = useCallback(async (payload) => {
    const { data } = await api.patch('/auth/me/', payload)
    setUser(data)
    return data
  }, [])

  useEffect(() => {
    const access = localStorage.getItem(TOKEN_KEYS.access)
    if (!access) {
      setLoading(false)
      return
    }

    fetchMe().catch(() => {}).finally(() => setLoading(false))

    const handleRefresh = () => {
      const currentAccess = localStorage.getItem(TOKEN_KEYS.access)
      if (currentAccess) {
        fetchMe().catch(() => {})
      }
    }
    window.addEventListener('budgetbuddy:data-refresh', handleRefresh)
    return () => window.removeEventListener('budgetbuddy:data-refresh', handleRefresh)
  }, [fetchMe])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, updateProfile, fetchMe }),
    [user, loading, login, register, logout, updateProfile, fetchMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider')
  }
  return context
}
