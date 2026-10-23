import { Link, NavLink, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext.jsx'

const roleStyles = {
  student: 'bg-sky-100 text-sky-700',
  premium: 'bg-amber-100 text-amber-700',
  admin: 'bg-violet-100 text-violet-700',
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="text-lg font-bold text-slate-900">
          Budget<span className="text-emerald-600">Buddy</span>
        </Link>

        <nav className="flex items-center gap-4 text-sm font-medium text-slate-600">
          <NavLink to="/" end className="hover:text-slate-900">
            Dashboard
          </NavLink>
          <NavLink to="/profile" className="hover:text-slate-900">
            Profile
          </NavLink>

          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${
              roleStyles[user?.role] ?? 'bg-slate-100 text-slate-600'
            }`}
          >
            {user?.role}
          </span>

          <span className="hidden text-slate-500 sm:inline">{user?.email}</span>

          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-white transition hover:bg-slate-700"
          >
            Logout
          </button>
        </nav>
      </div>
    </header>
  )
}
