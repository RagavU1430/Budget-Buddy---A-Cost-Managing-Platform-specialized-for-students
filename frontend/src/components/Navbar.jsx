import { useState } from 'react'
import { BarChart3, LayoutDashboard, LogOut, Receipt, Target, User, Wallet, Menu, X } from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext.jsx'
import NotificationBell from './NotificationBell.jsx'

const roleStyles = {
  student: 'bg-info-soft text-info ring-info/30',
  premium: 'bg-warn-soft text-warn ring-warn/30',
  admin: 'bg-accent-soft text-accent ring-accent/30',
}

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/transactions', label: 'Transactions', icon: Receipt },
  { to: '/budgets', label: 'Budgets', icon: Target },
  { to: '/goals', label: 'Goals 🎯', icon: Target },
  { to: '/analytics', label: 'Analytics 📊', icon: BarChart3 },
  { to: '/profile', label: 'Profile', icon: User },
]

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const linkClass = ({ isActive }) =>
    `relative flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-colors duration-200 ${
      isActive ? 'bg-accent-soft text-fg' : 'text-fg-muted hover:bg-white/5 hover:text-fg'
    }`

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft ring-1 ring-accent/30">
            <Wallet className="h-4.5 w-4.5 text-accent" aria-hidden="true" />
          </span>
          <span className="text-lg font-bold tracking-tight text-fg">
            Budget<span className="text-accent">Buddy</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              {({ isActive }) => (
                <>
                  <item.icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                  {isActive ? (
                    <span className="absolute inset-x-3 -bottom-px h-px bg-accent" aria-hidden="true" />
                  ) : null}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2.5">
          <NotificationBell />
          <span
            className={`hidden rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider ring-1 sm:inline-block ${
              roleStyles[user?.role] ?? 'bg-white/5 text-fg-muted ring-line'
            }`}
          >
            {user?.role}
          </span>
          <span className="hidden max-w-[160px] truncate text-sm text-fg-muted lg:inline">
            {user?.email}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="cursor-pointer rounded-full border border-line bg-white/5 px-3.5 py-1.5 text-sm font-medium text-fg transition-colors duration-200 hover:border-danger/40 hover:bg-danger-soft hover:text-danger"
          >
            <span className="flex items-center gap-1.5">
              <LogOut className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Logout</span>
            </span>
          </button>

          {/* Mobile menu toggle */}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={open ? 'Close menu' : 'Open menu'}
            className="cursor-pointer rounded-full border border-line bg-white/5 p-2 text-fg md:hidden"
          >
            {open ? <X className="h-4.5 w-4.5" aria-hidden="true" /> : <Menu className="h-4.5 w-4.5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open ? (
        <nav className="border-t border-line bg-background/95 px-4 py-3 md:hidden" aria-label="Mobile">
          <div className="flex flex-col gap-1">
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setOpen(false)} className={linkClass}>
                {({ isActive }) => (
                  <>
                    <item.icon className="h-4.5 w-4.5" aria-hidden="true" />
                    {item.label}
                    {isActive ? <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" /> : null}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </nav>
      ) : null}
    </header>
  )
}
