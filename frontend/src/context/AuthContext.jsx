import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import api, { TOKEN_KEYS } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me/')
      setUser(data)
      return data
    } catch {
      setUser(null)
      throw new Error('Not authenticated')
    }
  }, [])

  const login = useCallback(
    async ({ email, password }) => {
      const { data } = await api.post('/auth/login/', { email, password })
      if (data.access) localStorage.setItem(TOKEN_KEYS.access, data.access)
      // Refresh token is now stored in httpOnly cookie by backend
      setUser(data.user)
      return data.user
    },
    [],
  )

  const register = useCallback(
    async (payload) => {
      const { data } = await api.post('/auth/register/', payload)
      if (data.access) localStorage.setItem(TOKEN_KEYS.access, data.access)
      // Refresh token is now stored in httpOnly cookie by backend
      setUser(data.user)
      return data.user
    },
    [],
  )

  const logout = useCallback(async () => {
    // Call backend logout endpoint to clear httpOnly cookies and blacklist JTI
    try {
      await api.post('/auth/logout/')
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem(TOKEN_KEYS.access)
    setUser(null)
    // Trigger a refresh to clear any cached state
    window.dispatchEvent(new Event('budgetbuddy:data-refresh'))
  }, [])

  const updateProfile = useCallback(async (payload) => {
    const { data } = await api.patch('/auth/me/', payload)
    setUser(data)
    return data
  }, [])

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await fetchMe()
      } catch {
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    checkAuth()

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
