import { useEffect, useState } from 'react'
import {
  CheckCircle2,
  Phone,
  Save,
  Shield,
  Sparkles,
  Wallet,
} from 'lucide-react'

import Alert from '../components/Alert.jsx'
import Badge from '../components/Badge.jsx'
import FormField, { inputClass } from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { formatError } from '../utils/errors.js'

const roleBadgeMap = {
  student: { label: 'Student Member', tone: 'sky' },
  premium: { label: 'Premium Tier', tone: 'amber' },
  admin: { label: 'System Administrator', tone: 'violet' },
}

export default function Profile() {
  const { user, updateProfile } = useAuth()
  const profile = user?.profile ?? {}

  const [form, setForm] = useState({
    phone: profile.phone ?? '',
    monthly_income: profile.monthly_income ?? 0,
    currency: profile.currency ?? 'INR',
  })
  const [status, setStatus] = useState({ message: '', type: 'error' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setForm({
      phone: profile.phone ?? '',
      monthly_income: profile.monthly_income ?? 0,
      currency: profile.currency ?? 'INR',
    })
  }, [profile.phone, profile.monthly_income, profile.currency])

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setStatus({ message: '', type: 'error' })
    try {
      await updateProfile({
        ...form,
        monthly_income: Number(form.monthly_income) || 0,
      })
      setStatus({ message: 'Profile and preferences updated successfully.', type: 'success' })
    } catch (err) {
      setStatus({ message: formatError(err), type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const userInitial = (user?.first_name?.[0] || user?.username?.[0] || user?.email?.[0] || 'U').toUpperCase()
  const roleConfig = roleBadgeMap[user?.role] || { label: user?.role, tone: 'neutral' }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Header Profile Hero Card */}
      <div className="glass-strong relative overflow-hidden rounded-3xl p-6 sm:p-8">
        <div
          className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-accent/15 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-24 left-10 h-64 w-64 rounded-full bg-info/10 blur-3xl"
          aria-hidden="true"
        />

        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-5">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-accent-hover text-2xl font-bold text-on-accent shadow-glow">
              {userInitial}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-bold tracking-tight text-fg font-['Outfit'] sm:text-3xl">
                  {user?.first_name ? `${user.first_name} ${user?.last_name || ''}` : user?.username}
                </h1>
                <Badge tone={roleConfig.tone}>{roleConfig.label}</Badge>
              </div>
              <p className="mt-1 text-sm text-fg-muted">{user?.email}</p>
              <div className="mt-2 flex items-center gap-3 text-xs text-fg-faint">
                <span>Member ID: #{user?.id || '—'}</span>
                <span>•</span>
                <span>Active Session</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-12">
        {/* Left Column: Form Details */}
        <div className="md:col-span-8">
          <div className="glass rounded-3xl p-6 sm:p-8 border border-line">
            <div className="mb-6 flex items-center justify-between border-b border-line pb-4">
              <div>
                <h2 className="text-lg font-bold text-fg font-['Outfit']">Financial Settings</h2>
                <p className="text-xs text-fg-muted mt-0.5">
                  Update your monthly income baseline and local currency formatting.
                </p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <Wallet className="h-4.5 w-4.5" />
              </div>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <Alert message={status.message} type={status.type} />

              <FormField
                label="Monthly Income (₹ / Target Allowance)"
                id="monthly_income"
                hint="Used as your monthly budget denominator for savings calculations"
              >
                <div className="relative">
                  <div className="pointer-events-none absolute left-3.5 top-3 flex items-center text-fg-faint text-sm font-semibold">
                    {form.currency === 'INR' ? '₹' : form.currency}
                  </div>
                  <input
                    id="monthly_income"
                    name="monthly_income"
                    type="number"
                    min="0"
                    step="1"
                    placeholder="25000"
                    className={`${inputClass} pl-10`}
                    value={form.monthly_income}
                    onChange={handleChange}
                  />
                </div>
              </FormField>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField label="Contact Phone Number" id="phone" hint="For payment reminders & security">
                  <div className="relative">
                    <Phone className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                    <input
                      id="phone"
                      name="phone"
                      type="tel"
                      placeholder="+91 98765 43210"
                      className={`${inputClass} pl-10`}
                      value={form.phone}
                      onChange={handleChange}
                    />
                  </div>
                </FormField>

                <FormField label="Default Currency" id="currency">
                  <select
                    id="currency"
                    name="currency"
                    className={inputClass}
                    value={form.currency}
                    onChange={handleChange}
                  >
                    <option value="INR">INR (₹) - Indian Rupee</option>
                    <option value="USD">USD ($) - US Dollar</option>
                    <option value="EUR">EUR (€) - Euro</option>
                    <option value="GBP">GBP (£) - British Pound</option>
                  </select>
                </FormField>
              </div>

              <div className="mt-4 pt-4 border-t border-line flex items-center justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-6 py-2.5 text-sm font-bold text-on-accent transition-all duration-200 hover:bg-accent-hover hover:shadow-glow disabled:opacity-60"
                >
                  {saving ? (
                    <>
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-on-accent border-t-transparent" />
                      <span>Saving Changes…</span>
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      <span>Save Profile</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Account Meta */}
        <div className="md:col-span-4 space-y-6">
          <div className="glass rounded-3xl p-6 border border-line">
            <h3 className="text-sm font-bold text-fg font-['Outfit']">Account Privileges</h3>
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-3 text-xs text-fg-muted">
                <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
                <span>Unlimited expense logging</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-fg-muted">
                <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
                <span>Category budget guardrails</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-fg-muted">
                <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
                <span>Monthly cashflow analytics</span>
              </div>
              {user?.role === 'admin' ? (
                <div className="flex items-center gap-3 text-xs text-accent font-semibold">
                  <Shield className="h-4 w-4 shrink-0" />
                  <span>Full Administrative Access</span>
                </div>
              ) : null}
            </div>
          </div>

          <div className="rounded-3xl border border-accent/20 bg-accent-soft/30 p-5 backdrop-blur-md">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Student Tip</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-fg-muted">
              Setting an accurate monthly income helps BudgetBuddy calculate your exact daily burn rate and safe daily spending limits.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
