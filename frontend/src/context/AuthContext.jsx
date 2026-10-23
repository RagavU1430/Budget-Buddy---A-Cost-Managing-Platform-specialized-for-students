import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import api, { TOKEN_KEYS } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const storeTokens = useCallback((tokens) => {
    localStorage.setItem(TOKEN_KEYS.access, tokens.access)
    localStorage.setItem(TOKEN_KEYS.refresh, tokens.refresh)
  }, [])

  const clearTokens = useCallback(() => {
    localStorage.removeItem(TOKEN_KEYS.access)
    localStorage.removeItem(TOKEN_KEYS.refresh)
  }, [])

  const fetchMe = useCallback(async () => {
    const { data } = await api.get('/api/auth/me/')
    setUser(data)
    return data
  }, [])

  const login = useCallback(
    async ({ email, password }) => {
      const { data } = await api.post('/api/auth/login/', { email, password })
      storeTokens(data)
      setUser(data.user)
      return data.user
    },
    [storeTokens],
  )

  const register = useCallback(
    async (payload) => {
      const { data } = await api.post('/api/auth/register/', payload)
      storeTokens(data)
      setUser(data.user)
      return data.user
    },
    [storeTokens],
  )

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [clearTokens])

  const updateProfile = useCallback(async (payload) => {
    const { data } = await api.patch('/api/auth/me/', payload)
    setUser(data)
    return data
  }, [])

  useEffect(() => {
    const access = localStorage.getItem(TOKEN_KEYS.access)
    if (!access) {
      setLoading(false)
      return
    }
    fetchMe()
      .catch(() => {
        clearTokens()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [fetchMe, clearTokens])

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
