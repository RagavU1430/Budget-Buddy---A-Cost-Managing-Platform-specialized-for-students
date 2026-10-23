import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import Alert from '../components/Alert.jsx'
import FormField from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { formatError } from '../utils/errors.js'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await login(form)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(formatError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">
          Budget<span className="text-emerald-600">Buddy</span>
        </h1>
        <p className="mt-1 text-sm text-slate-500">Sign in to manage your student budget.</p>

        <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
          <Alert message={error} />

          <FormField label="Email" id="email">
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={handleChange}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            />
          </FormField>

          <FormField label="Password" id="password">
            <input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="current-password"
              value={form.password}
              onChange={handleChange}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            />
          </FormField>

          <button
            type="submit"
            disabled={submitting}
            className="cursor-pointer rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60 shadow-sm"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="mt-6 border-t border-slate-100 pt-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Quick Fill Demo Roles
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, email: 'student@budgetbuddy.local' }))}
              className="rounded-lg border border-sky-200 bg-sky-50 px-2 py-1.5 text-xs font-medium text-sky-700 hover:bg-sky-100 transition text-center"
            >
              🎓 Student
            </button>
            <button
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, email: 'premium@budgetbuddy.local' }))}
              className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition text-center"
            >
              ⭐ Premium
            </button>
            <button
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, email: 'admin@budgetbuddy.local' }))}
              className="rounded-lg border border-violet-200 bg-violet-50 px-2 py-1.5 text-xs font-medium text-violet-700 hover:bg-violet-100 transition text-center"
            >
              🛡️ Admin
            </button>
          </div>
          <p className="mt-2 text-[11px] text-slate-400 text-center">
            Populates demo account email; enter your password to sign in.
          </p>
        </div>

        <p className="mt-5 text-center text-sm text-slate-600">
          New to BudgetBuddy?{' '}
          <Link to="/register" className="font-semibold text-emerald-700 hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
