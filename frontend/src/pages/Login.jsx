import { useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  Database,
  Eye,
  EyeOff,
  Lock,
  Mail,
  PieChart,
  ShieldCheck,
  Sparkles,
  Wallet,
} from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import Alert from '../components/Alert.jsx'
import FormField, { inputClass } from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { formatError } from '../utils/errors.js'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12 sm:px-6 lg:px-8">
      {/* Ambient background glows */}
      <div
        className="pointer-events-none absolute -top-40 -right-40 h-96 w-96 rounded-full bg-accent/20 blur-[110px]"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-info/15 blur-[110px]"
        aria-hidden="true"
      />

      <div className="relative mx-auto grid w-full max-w-4xl items-center gap-10 lg:grid-cols-12">
        {/* Left Side: Brand & Value Props */}
        <div className="hidden lg:col-span-5 lg:flex lg:flex-col lg:justify-between space-y-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent-soft px-3.5 py-1 text-xs font-semibold text-accent shadow-sm">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Campus Finance Operating System</span>
            </div>

            <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-fg font-['Outfit'] sm:text-5xl">
              Welcome back to <span className="text-accent drop-shadow-[0_0_25px_rgba(16,185,129,0.4)]">BudgetBuddy</span>.
            </h1>

            <p className="mt-4 text-base leading-relaxed text-fg-muted">
              Log in to track everyday transactions, verify remaining monthly caps, and stay completely in control of your student budget.
            </p>
          </div>

          {/* Features Highlights */}
          <div className="rounded-2xl border border-line bg-surface/70 p-5 backdrop-blur-md space-y-3.5">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                <Database className="h-4 w-4" />
              </div>
              <div>
                <div className="text-xs font-semibold text-fg">Supabase Cloud Database</div>
                <div className="text-[11px] text-fg-muted">Real-time persistent PostgreSQL storage for all your financial records</div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-info-soft text-info">
                <PieChart className="h-4 w-4" />
              </div>
              <div>
                <div className="text-xs font-semibold text-fg">Smart Budgeting & Caps</div>
                <div className="text-[11px] text-fg-muted">Track monthly expenses against custom category limits</div>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warn-soft text-warn">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <div className="text-xs font-semibold text-fg">Secure Auth & Privacy</div>
                <div className="text-[11px] text-fg-muted">Encrypted password hashing with automated JWT session renewal</div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-fg-faint">
            <CheckCircle2 className="h-4 w-4 text-accent" />
            <span>Connected to Production Supabase Database</span>
          </div>
        </div>

        {/* Right Card: Login Form */}
        <div className="lg:col-span-7">
          <div className="glass-strong relative rounded-3xl p-7 sm:p-10 shadow-2xl border border-line-strong">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft ring-1 ring-accent/30">
                  <Wallet className="h-5 w-5 text-accent" />
                </span>
                <span className="text-xl font-bold tracking-tight text-fg font-['Outfit']">
                  Budget<span className="text-accent">Buddy</span>
                </span>
              </div>
              <span className="flex items-center gap-1.5 rounded-full border border-line bg-surface/60 px-3 py-1 text-xs font-medium text-accent">
                <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                Live Cloud API
              </span>
            </div>

            <div className="mt-6">
              <h2 className="text-2xl font-bold tracking-tight text-fg font-['Outfit'] sm:text-3xl">
                Sign in to your account
              </h2>
              <p className="mt-1 text-sm text-fg-muted">
                Enter your credentials to access your financial dashboard.
              </p>
            </div>

            <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
              <Alert message={error} />

              <FormField label="Email address" id="email">
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="you@example.com"
                    className={`${inputClass} pl-10`}
                    value={form.email}
                    onChange={handleChange}
                  />
                </div>
              </FormField>

              <FormField label="Password" id="password">
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    placeholder="••••••••"
                    className={`${inputClass} pl-10 pr-10`}
                    value={form.password}
                    onChange={handleChange}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-fg-faint hover:text-fg transition-colors"
                    aria-label="Toggle password visibility"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </FormField>

              <button
                type="submit"
                disabled={submitting}
                className="mt-2 inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-bold text-on-accent transition-all duration-200 hover:bg-accent-hover hover:shadow-glow disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-on-accent border-t-transparent" />
                    <span>Signing in…</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-fg-muted">
              Don't have an account yet?{' '}
              <Link to="/register" className="font-semibold text-accent hover:underline">
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
