import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Wallet } from 'lucide-react'

import { useAuth } from '../context/AuthContext.jsx'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background text-fg">
        <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-soft text-accent ring-1 ring-accent/30 shadow-glow">
          <Wallet className="h-7 w-7 animate-pulse text-accent" />
          <div className="absolute inset-0 rounded-2xl border-2 border-accent/40 border-t-transparent animate-spin" />
        </div>
        <div className="text-center">
          <div className="text-sm font-semibold tracking-wide text-fg font-['Outfit']">
            Budget<span className="text-accent">Buddy</span>
          </div>
          <p className="mt-0.5 text-xs text-fg-muted">Securing your session…</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <Outlet />
}
