import { useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  User,
  Wallet,
} from 'lucide-react'

import { Link, useNavigate } from 'react-router-dom'

import Alert from '../components/Alert.jsx'
import FormField, { inputClass } from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { formatError } from '../utils/errors.js'

const initialForm = {
  first_name: '',
  last_name: '',
  email: '',
  username: '',
  role: 'student',
  password: '',
  password_confirm: '',
}

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({
      ...current,
      [name]: value,
      // Auto-populate username from email if username is empty or mirrors email
      ...(name === 'email' && (!current.username || current.username === current.email.split('@')[0])
        ? { username: value.split('@')[0] }
        : {}),
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (form.password !== form.password_confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await register(form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(formatError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12 sm:px-6 lg:px-8">
      {/* Dynamic ambient lights */}
      <div
        className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-accent/20 blur-[100px]"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-info/15 blur-[100px]"
        aria-hidden="true"
      />

      <div className="relative mx-auto grid w-full max-w-5xl items-center gap-10 lg:grid-cols-12">
        {/* Left branding showcase (visible on large screens) */}
        <div className="hidden lg:col-span-5 lg:flex lg:flex-col lg:justify-between space-y-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent-soft px-3.5 py-1 text-xs font-semibold text-accent shadow-sm">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Smart Student Finance</span>
            </div>

            <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-fg font-['Outfit'] sm:text-5xl">
              Take charge of your <span className="text-accent drop-shadow-[0_0_25px_rgba(16,185,129,0.4)]">money</span>.
            </h1>

            <p className="mt-4 text-base leading-relaxed text-fg-muted">
              Built specifically for college life. Track mess bills, rent, daily canteen expenses, and academic budgets with zero stress.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-start gap-3.5 rounded-2xl border border-line bg-surface/60 p-4 backdrop-blur-md">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent ring-1 ring-accent/30">
                <GraduationCap className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-fg">Student Budget Guardrails</h4>
                <p className="text-xs text-fg-muted mt-0.5">Real-time alerts before you run out of funds mid-semester.</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 rounded-2xl border border-line bg-surface/60 p-4 backdrop-blur-md">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-info-soft text-info ring-1 ring-info/30">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-fg">Visual Expense Insights</h4>
                <p className="text-xs text-fg-muted mt-0.5">Categorized breakdown of food, books, tech, and entertainment.</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 rounded-2xl border border-line bg-surface/60 p-4 backdrop-blur-md">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-warn-soft text-warn ring-1 ring-warn/30">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-fg">Private & Secure</h4>
                <p className="text-xs text-fg-muted mt-0.5">JWT token authentication with enterprise-grade data protection.</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2 text-xs text-fg-faint">
            <CheckCircle2 className="h-4 w-4 text-accent" />
            <span>Free for students • Instant activation • No hidden charges</span>
          </div>
        </div>

        {/* Right Registration Card */}
        <div className="lg:col-span-7">
          <div className="glass-strong relative rounded-3xl p-7 sm:p-10 shadow-2xl border border-line-strong">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft ring-1 ring-accent/30">
                  <Wallet className="h-5 w-5 text-accent" />
                </span>
                <span className="text-xl font-bold tracking-tight text-fg font-['Outfit']">
                  Budget<span className="text-accent">Buddy</span>
                </span>
              </div>

              <span className="rounded-full border border-line bg-surface/60 px-3 py-1 text-xs font-medium text-fg-muted">
                Step 1 of 1
              </span>
            </div>

            <div className="mt-6">
              <h2 className="text-2xl font-bold tracking-tight text-fg font-['Outfit'] sm:text-3xl">
                Create your student account
              </h2>
              <p className="mt-1 text-sm text-fg-muted">
                Start tracking in under 60 seconds with your personalized profile.
              </p>
            </div>

            <form className="mt-7 flex flex-col gap-4" onSubmit={handleSubmit}>
              <Alert message={error} />

              {/* Name fields */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <FormField label="First name" id="first_name">
                  <div className="relative">
                    <User className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                    <input
                      id="first_name"
                      name="first_name"
                      required
                      placeholder="e.g. Ragav"
                      className={`${inputClass} pl-10`}
                      value={form.first_name}
                      onChange={handleChange}
                    />
                  </div>
                </FormField>

                <FormField label="Last name" id="last_name">
                  <input
                    id="last_name"
                    name="last_name"
                    required
                    placeholder="e.g. U"
                    className={inputClass}
                    value={form.last_name}
                    onChange={handleChange}
                  />
                </FormField>
              </div>

              {/* Email & Username */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <FormField label="Email address" id="email">
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      autoComplete="email"
                      placeholder="you@college.edu"
                      className={`${inputClass} pl-10`}
                      value={form.email}
                      onChange={handleChange}
                    />
                  </div>
                </FormField>

                <FormField label="Username" id="username">
                  <input
                    id="username"
                    name="username"
                    required
                    autoComplete="username"
                    placeholder="ragavu14"
                    className={inputClass}
                    value={form.username}
                    onChange={handleChange}
                  />
                </FormField>
              </div>

              {/* Role Selection */}
              <FormField label="Select Account Type" id="role">
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setForm((c) => ({ ...c, role: 'student' }))}
                    className={`flex items-center gap-3 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                      form.role === 'student'
                        ? 'border-accent bg-accent-soft/30 text-fg ring-1 ring-accent/40 shadow-sm'
                        : 'border-line bg-surface/40 text-fg-muted hover:border-line-strong hover:bg-surface/70'
                    }`}
                  >
                    <span className="text-xl">🎓</span>
                    <div>
                      <div className="text-xs font-semibold text-fg">Student</div>
                      <div className="text-[11px] text-fg-faint">Standard budget tools</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setForm((c) => ({ ...c, role: 'premium' }))}
                    className={`flex items-center gap-3 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                      form.role === 'premium'
                        ? 'border-warn bg-warn-soft/30 text-fg ring-1 ring-warn/40 shadow-sm'
                        : 'border-line bg-surface/40 text-fg-muted hover:border-line-strong hover:bg-surface/70'
                    }`}
                  >
                    <span className="text-xl">⭐</span>
                    <div>
                      <div className="text-xs font-semibold text-fg">Premium</div>
                      <div className="text-[11px] text-fg-faint">Advanced analytics</div>
                    </div>
                  </button>
                </div>
              </FormField>

              {/* Passwords */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <FormField label="Password" id="password">
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      autoComplete="new-password"
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

                <FormField label="Confirm Password" id="password_confirm">
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                    <input
                      id="password_confirm"
                      name="password_confirm"
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      autoComplete="new-password"
                      placeholder="••••••••"
                      className={`${inputClass} pl-10 pr-10`}
                      value={form.password_confirm}
                      onChange={handleChange}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-2.5 text-fg-faint hover:text-fg transition-colors"
                      aria-label="Toggle password visibility"
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </FormField>
              </div>

              {/* Submit CTA */}
              <button
                type="submit"
                disabled={submitting}
                className="mt-3 inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-bold text-on-accent transition-all duration-200 hover:bg-accent-hover hover:shadow-glow disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-on-accent border-t-transparent" />
                    <span>Creating your account…</span>
                  </>
                ) : (
                  <>
                    <span>Create Free Account</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Footer switcher */}
            <p className="mt-6 text-center text-sm text-fg-muted">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-accent hover:underline">
                Sign in here
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
