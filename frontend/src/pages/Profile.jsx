import { useEffect, useState } from 'react'
import {
  AlertCircle,
  AtSign,
  BadgeCheck,
  Calendar,
  CheckCircle2,
  DollarSign,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  LogOut,
  Mail,
  Phone,
  Save,
  Shield,
  Sliders,
  Sparkles,
  User,
  Wallet,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import Alert from '../components/Alert.jsx'
import Badge from '../components/Badge.jsx'
import FormField, { inputClass } from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api/client.js'
import { formatError } from '../utils/errors.js'

const roleBadgeMap = {
  student: { label: 'Student Member', tone: 'sky', icon: '🎓' },
  premium: { label: 'Premium Tier', tone: 'amber', icon: '⭐' },
  admin: { label: 'System Administrator', tone: 'violet', icon: '🛡️' },
}

const CURRENCIES = [
  { code: 'INR', symbol: '₹', name: 'Indian Rupee' },
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '€', name: 'Euro' },
  { code: 'GBP', symbol: '£', name: 'British Pound' },
  { code: 'CAD', symbol: 'CA$', name: 'Canadian Dollar' },
  { code: 'AUD', symbol: 'AU$', name: 'Australian Dollar' },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar' },
]

export default function Profile() {
  const { user, updateProfile, logout } = useAuth()
  const navigate = useNavigate()
  const profile = user?.profile ?? {}

  const [activeTab, setActiveTab] = useState('personal') // 'personal' | 'financial' | 'security' | 'overview'

  // Personal Info form
  const [personalForm, setPersonalForm] = useState({
    first_name: user?.first_name ?? '',
    last_name: user?.last_name ?? '',
    username: user?.username ?? '',
    phone: profile?.phone ?? '',
    avatar_url: profile?.avatar_url ?? '',
  })

  // Financial Settings form
  const [financialForm, setFinancialForm] = useState({
    monthly_income: profile?.monthly_income ?? 0,
    currency: profile?.currency ?? 'INR',
    savings_target: profile?.financial_preferences?.savings_target_percent ?? 20,
    alert_threshold: profile?.financial_preferences?.alert_threshold_percent ?? 85,
  })

  // Password Change form
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)

  // Status & saving indicators
  const [status, setStatus] = useState({ message: '', type: 'error' })
  const [saving, setSaving] = useState(false)
  const [passwordStatus, setPasswordStatus] = useState({ message: '', type: 'error' })
  const [passwordSaving, setPasswordSaving] = useState(false)

  useEffect(() => {
    setPersonalForm({
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      username: user?.username ?? '',
      phone: profile?.phone ?? '',
      avatar_url: profile?.avatar_url ?? '',
    })
    setFinancialForm({
      monthly_income: profile?.monthly_income ?? 0,
      currency: profile?.currency ?? 'INR',
      savings_target: profile?.financial_preferences?.savings_target_percent ?? 20,
      alert_threshold: profile?.financial_preferences?.alert_threshold_percent ?? 85,
    })
  }, [user, profile])

  const handlePersonalChange = (e) => {
    const { name, value } = e.target
    setPersonalForm((curr) => ({ ...curr, [name]: value }))
  }

  const handleFinancialChange = (e) => {
    const { name, value } = e.target
    setFinancialForm((curr) => ({ ...curr, [name]: value }))
  }

  const handlePasswordChange = (e) => {
    const { name, value } = e.target
    setPasswordForm((curr) => ({ ...curr, [name]: value }))
  }

  // Save Personal Details
  const handleSavePersonal = async (e) => {
    e.preventDefault()
    setSaving(true)
    setStatus({ message: '', type: 'error' })
    try {
      await updateProfile({
        first_name: personalForm.first_name,
        last_name: personalForm.last_name,
        username: personalForm.username,
        phone: personalForm.phone,
        avatar_url: personalForm.avatar_url,
      })
      setStatus({ message: 'Personal information updated successfully!', type: 'success' })
    } catch (err) {
      setStatus({ message: formatError(err), type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  // Save Financial Details
  const handleSaveFinancial = async (e) => {
    e.preventDefault()
    setSaving(true)
    setStatus({ message: '', type: 'error' })
    try {
      await updateProfile({
        monthly_income: Number(financialForm.monthly_income) || 0,
        currency: financialForm.currency,
        financial_preferences: {
          ...profile.financial_preferences,
          savings_target_percent: Number(financialForm.savings_target) || 20,
          alert_threshold_percent: Number(financialForm.alert_threshold) || 85,
        },
      })
      setStatus({ message: 'Financial preferences and allowances updated successfully!', type: 'success' })
    } catch (err) {
      setStatus({ message: formatError(err), type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  // Submit Password Change
  const handleChangePassword = async (e) => {
    e.preventDefault()
    setPasswordStatus({ message: '', type: 'error' })

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordStatus({ message: 'New password and confirmation do not match.', type: 'error' })
      return
    }
    if (passwordForm.new_password.length < 8) {
      setPasswordStatus({ message: 'New password must be at least 8 characters long.', type: 'error' })
      return
    }

    setPasswordSaving(true)
    try {
      await api.post('/api/auth/change-password/', {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      })
      setPasswordStatus({ message: 'Password changed successfully! Keep it secure.', type: 'success' })
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (err) {
      setPasswordStatus({ message: formatError(err), type: 'error' })
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const roleConfig = roleBadgeMap[user?.role] || { label: user?.role, tone: 'neutral', icon: '👤' }
  const userInitial = (personalForm.first_name?.[0] || personalForm.username?.[0] || user?.email?.[0] || 'U').toUpperCase()
  const activeCurrencySymbol = CURRENCIES.find((c) => c.code === financialForm.currency)?.symbol || '₹'

  // Formatted date joined
  const formattedJoinedDate = user?.date_joined
    ? new Date(user.date_joined).toLocaleDateString('en-US', {
        month: 'short',
        year: 'numeric',
        day: 'numeric',
      })
    : 'Recently Joined'

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-12">
      {/* 1. Header Profile Hero Card */}
      <div className="glass-strong relative overflow-hidden rounded-3xl p-6 sm:p-8 border border-line">
        <div
          className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-accent/20 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-24 left-10 h-64 w-64 rounded-full bg-info/15 blur-3xl"
          aria-hidden="true"
        />

        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
            {/* Avatar Preview */}
            <div className="relative group">
              {personalForm.avatar_url ? (
                <img
                  src={personalForm.avatar_url}
                  alt={user?.username}
                  className="h-20 w-20 rounded-2xl object-cover ring-2 ring-accent/40 shadow-glow"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
              ) : null}
              <div
                className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-emerald-600 text-3xl font-extrabold text-on-accent shadow-glow transition-transform duration-200 group-hover:scale-105 ${
                  personalForm.avatar_url ? 'hidden' : ''
                }`}
              >
                {userInitial}
              </div>
              <span className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-surface border border-line text-xs shadow-sm">
                {roleConfig.icon}
              </span>
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-extrabold tracking-tight text-fg font-['Outfit'] sm:text-3xl">
                  {personalForm.first_name
                    ? `${personalForm.first_name} ${personalForm.last_name}`
                    : user?.username || 'User Profile'}
                </h1>
                <Badge tone={roleConfig.tone}>{roleConfig.label}</Badge>
              </div>

              <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-fg-muted">
                <span className="font-medium text-accent">@{personalForm.username || user?.username}</span>
                <span>•</span>
                <span>{user?.email}</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400 border border-emerald-500/20">
                  <BadgeCheck className="h-3 w-3" />
                  Verified
                </span>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-fg-faint">
                <span className="inline-flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-accent" />
                  Member ID: #{user?.id || '—'}
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 text-info" />
                  Joined {formattedJoinedDate}
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  Active Session
                </span>
              </div>
            </div>
          </div>

          {/* Quick stats pills */}
          <div className="flex sm:flex-col gap-2 shrink-0 border-t border-line/60 pt-4 sm:border-t-0 sm:pt-0">
            <div className="rounded-xl border border-line bg-surface/80 px-3.5 py-2 backdrop-blur-md">
              <div className="text-[10px] uppercase tracking-wider text-fg-faint font-semibold">Monthly Allowance</div>
              <div className="text-sm font-bold text-fg">
                {activeCurrencySymbol} {Number(financialForm.monthly_income).toLocaleString()}
              </div>
            </div>
            <div className="rounded-xl border border-line bg-surface/80 px-3.5 py-2 backdrop-blur-md">
              <div className="text-[10px] uppercase tracking-wider text-fg-faint font-semibold">Default Currency</div>
              <div className="text-sm font-bold text-accent">{financialForm.currency}</div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Interactive Navigation Tabs */}
      <div className="flex border-b border-line gap-2 overflow-x-auto pb-px">
        {[
          { id: 'personal', label: 'Personal Information', icon: User },
          { id: 'financial', label: 'Financial Settings', icon: Wallet },
          { id: 'security', label: 'Security & Password', icon: Lock },
          { id: 'overview', label: 'Account Overview', icon: Shield },
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setActiveTab(tab.id)
                setStatus({ message: '', type: 'error' })
                setPasswordStatus({ message: '', type: 'error' })
              }}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold rounded-t-2xl transition-all cursor-pointer whitespace-nowrap border-b-2 -mb-px ${
                isActive
                  ? 'border-accent text-accent bg-accent-soft/40 shadow-sm'
                  : 'border-transparent text-fg-muted hover:text-fg hover:bg-white/5'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-12">
        {/* Left Column: Active Tab Content */}
        <div className="md:col-span-8 space-y-6">
          <Alert message={status.message} type={status.type} />

          {/* TAB 1: PERSONAL INFORMATION */}
          {activeTab === 'personal' && (
            <div className="glass rounded-3xl p-6 sm:p-8 border border-line">
              <div className="mb-6 flex items-center justify-between border-b border-line pb-4">
                <div>
                  <h2 className="text-lg font-bold text-fg font-['Outfit']">Personal Information</h2>
                  <p className="text-xs text-fg-muted mt-0.5">
                    View and update your display name, public username, and contact phone number.
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <User className="h-4.5 w-4.5" />
                </div>
              </div>

              <form onSubmit={handleSavePersonal} className="flex flex-col gap-5">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField label="First Name" id="first_name" hint="Given name">
                    <input
                      id="first_name"
                      name="first_name"
                      type="text"
                      placeholder="e.g. Rahul"
                      className={inputClass}
                      value={personalForm.first_name}
                      onChange={handlePersonalChange}
                    />
                  </FormField>

                  <FormField label="Last Name" id="last_name" hint="Family name">
                    <input
                      id="last_name"
                      name="last_name"
                      type="text"
                      placeholder="e.g. Sharma"
                      className={inputClass}
                      value={personalForm.last_name}
                      onChange={handlePersonalChange}
                    />
                  </FormField>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField label="Username" id="username" hint="Unique public handle">
                    <div className="relative">
                      <AtSign className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                      <input
                        id="username"
                        name="username"
                        type="text"
                        required
                        placeholder="student_user"
                        className={`${inputClass} pl-10`}
                        value={personalForm.username}
                        onChange={handlePersonalChange}
                      />
                    </div>
                  </FormField>

                  <FormField label="Email Address" id="email" hint="Primary login credential (read-only)">
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                      <input
                        id="email"
                        type="email"
                        readOnly
                        disabled
                        value={user?.email || ''}
                        className={`${inputClass} pl-10 opacity-70 cursor-not-allowed bg-surface/50`}
                      />
                    </div>
                  </FormField>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField label="Contact Phone Number" id="phone" hint="For SMS alerts & verification">
                    <div className="relative">
                      <Phone className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                      <input
                        id="phone"
                        name="phone"
                        type="tel"
                        placeholder="+91 98765 43210"
                        className={`${inputClass} pl-10`}
                        value={personalForm.phone}
                        onChange={handlePersonalChange}
                      />
                    </div>
                  </FormField>

                  <FormField label="Profile Avatar URL (Optional)" id="avatar_url" hint="Direct link to JPG/PNG image">
                    <input
                      id="avatar_url"
                      name="avatar_url"
                      type="url"
                      placeholder="https://images.unsplash.com/..."
                      className={inputClass}
                      value={personalForm.avatar_url}
                      onChange={handlePersonalChange}
                    />
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
                        <span>Save Personal Info</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 2: FINANCIAL SETTINGS */}
          {activeTab === 'financial' && (
            <div className="glass rounded-3xl p-6 sm:p-8 border border-line">
              <div className="mb-6 flex items-center justify-between border-b border-line pb-4">
                <div>
                  <h2 className="text-lg font-bold text-fg font-['Outfit']">Financial Settings & Allowances</h2>
                  <p className="text-xs text-fg-muted mt-0.5">
                    Configure your monthly income baseline, currency formatting, and budget guardrails.
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <Wallet className="h-4.5 w-4.5" />
                </div>
              </div>

              <form onSubmit={handleSaveFinancial} className="flex flex-col gap-5">
                <FormField
                  label={`Monthly Income / Allowance (${activeCurrencySymbol})`}
                  id="monthly_income"
                  hint="Used as your monthly budget denominator for savings and burn rate calculations"
                >
                  <div className="relative">
                    <div className="pointer-events-none absolute left-3.5 top-3 flex items-center text-fg-faint text-sm font-bold">
                      {activeCurrencySymbol}
                    </div>
                    <input
                      id="monthly_income"
                      name="monthly_income"
                      type="number"
                      min="0"
                      step="1"
                      required
                      placeholder="50000"
                      className={`${inputClass} pl-10 font-medium`}
                      value={financialForm.monthly_income}
                      onChange={handleFinancialChange}
                    />
                  </div>
                </FormField>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField label="Default Currency" id="currency" hint="All transactions display in this unit">
                    <select
                      id="currency"
                      name="currency"
                      className={inputClass}
                      value={financialForm.currency}
                      onChange={handleFinancialChange}
                    >
                      {CURRENCIES.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.code} ({c.symbol}) - {c.name}
                        </option>
                      ))}
                    </select>
                  </FormField>

                  <FormField label="Target Monthly Savings (%)" id="savings_target" hint="Recommended: 15% – 30%">
                    <div className="relative">
                      <input
                        id="savings_target"
                        name="savings_target"
                        type="number"
                        min="0"
                        max="90"
                        step="1"
                        placeholder="20"
                        className={inputClass}
                        value={financialForm.savings_target}
                        onChange={handleFinancialChange}
                      />
                      <span className="pointer-events-none absolute right-3.5 top-3 text-xs text-fg-faint">%</span>
                    </div>
                  </FormField>
                </div>

                <div className="rounded-2xl border border-line bg-surface/50 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-semibold text-fg">Budget Overspending Alert Trigger</div>
                      <div className="text-xs text-fg-muted mt-0.5">
                        BudgetBuddy alerts you via toast notifications when any category hits this capacity
                      </div>
                    </div>
                    <span className="rounded-lg bg-accent-soft px-2.5 py-1 text-xs font-bold text-accent">
                      {financialForm.alert_threshold}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="100"
                    step="5"
                    name="alert_threshold"
                    value={financialForm.alert_threshold}
                    onChange={handleFinancialChange}
                    className="mt-3 w-full accent-accent cursor-pointer"
                  />
                  <div className="flex justify-between text-[11px] text-fg-faint mt-1">
                    <span>50% (Early warning)</span>
                    <span>85% (Recommended)</span>
                    <span>100% (Hard limit)</span>
                  </div>
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
                        <span>Saving Preferences…</span>
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        <span>Save Financial Settings</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 3: SECURITY & PASSWORD */}
          {activeTab === 'security' && (
            <div className="glass rounded-3xl p-6 sm:p-8 border border-line">
              <div className="mb-6 flex items-center justify-between border-b border-line pb-4">
                <div>
                  <h2 className="text-lg font-bold text-fg font-['Outfit']">Change Password & Security</h2>
                  <p className="text-xs text-fg-muted mt-0.5">
                    Update your account login password with Argon2 encryption.
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <KeyRound className="h-4.5 w-4.5" />
                </div>
              </div>

              <Alert message={passwordStatus.message} type={passwordStatus.type} />

              <form onSubmit={handleChangePassword} className="flex flex-col gap-5">
                <FormField label="Current Password" id="current_password" hint="Enter your existing account password">
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                    <input
                      id="current_password"
                      name="current_password"
                      type={showCurrentPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      className={`${inputClass} pl-10 pr-10`}
                      value={passwordForm.current_password}
                      onChange={handlePasswordChange}
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword((prev) => !prev)}
                      className="absolute right-3.5 top-3 text-fg-faint hover:text-fg cursor-pointer"
                    >
                      {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </FormField>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <FormField label="New Password" id="new_password" hint="Minimum 8 characters">
                    <div className="relative">
                      <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                      <input
                        id="new_password"
                        name="new_password"
                        type={showNewPassword ? 'text' : 'password'}
                        required
                        placeholder="••••••••••••"
                        className={`${inputClass} pl-10 pr-10`}
                        value={passwordForm.new_password}
                        onChange={handlePasswordChange}
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword((prev) => !prev)}
                        className="absolute right-3.5 top-3 text-fg-faint hover:text-fg cursor-pointer"
                      >
                        {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </FormField>

                  <FormField label="Confirm New Password" id="confirm_password" hint="Must match new password exactly">
                    <div className="relative">
                      <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-fg-faint" />
                      <input
                        id="confirm_password"
                        name="confirm_password"
                        type={showNewPassword ? 'text' : 'password'}
                        required
                        placeholder="••••••••••••"
                        className={`${inputClass} pl-10`}
                        value={passwordForm.confirm_password}
                        onChange={handlePasswordChange}
                      />
                    </div>
                  </FormField>
                </div>

                <div className="mt-4 pt-4 border-t border-line flex items-center justify-end">
                  <button
                    type="submit"
                    disabled={passwordSaving}
                    className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-6 py-2.5 text-sm font-bold text-on-accent transition-all duration-200 hover:bg-accent-hover hover:shadow-glow disabled:opacity-60"
                  >
                    {passwordSaving ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-on-accent border-t-transparent" />
                        <span>Updating Password…</span>
                      </>
                    ) : (
                      <>
                        <KeyRound className="h-4 w-4" />
                        <span>Update Password</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 4: ACCOUNT OVERVIEW & DETAILS */}
          {activeTab === 'overview' && (
            <div className="glass rounded-3xl p-6 sm:p-8 border border-line space-y-6">
              <div className="flex items-center justify-between border-b border-line pb-4">
                <div>
                  <h2 className="text-lg font-bold text-fg font-['Outfit']">Account Overview & Diagnostic Metadata</h2>
                  <p className="text-xs text-fg-muted mt-0.5">
                    Technical session parameters, permission levels, and registration timeline.
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <Shield className="h-4.5 w-4.5" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-line bg-surface/40 p-4">
                  <div className="text-xs text-fg-faint font-semibold uppercase tracking-wider">Account ID</div>
                  <div className="mt-1 text-base font-bold text-fg">#{user?.id}</div>
                </div>

                <div className="rounded-2xl border border-line bg-surface/40 p-4">
                  <div className="text-xs text-fg-faint font-semibold uppercase tracking-wider">Assigned Role</div>
                  <div className="mt-1 text-base font-bold text-accent capitalize">{user?.role}</div>
                </div>

                <div className="rounded-2xl border border-line bg-surface/40 p-4">
                  <div className="text-xs text-fg-faint font-semibold uppercase tracking-wider">Registration Date</div>
                  <div className="mt-1 text-sm font-medium text-fg">{formattedJoinedDate}</div>
                </div>

                <div className="rounded-2xl border border-line bg-surface/40 p-4">
                  <div className="text-xs text-fg-faint font-semibold uppercase tracking-wider">Administrative Staff</div>
                  <div className="mt-1 text-sm font-medium text-fg">{user?.is_staff ? 'Yes (Granted)' : 'No (Standard)'}</div>
                </div>

                <div className="rounded-2xl border border-line bg-surface/40 p-4">
                  <div className="text-xs text-fg-faint font-semibold uppercase tracking-wider">Session Token Lifespan</div>
                  <div className="mt-1 text-sm font-medium text-fg">60 Minutes (Auto-refreshed via JWT)</div>
                </div>

                <div className="rounded-2xl border border-line bg-surface/40 p-4">
                  <div className="text-xs text-fg-faint font-semibold uppercase tracking-wider">Security Tier</div>
                  <div className="mt-1 text-sm font-medium text-fg">Argon2 Password Hashing & CORS Guard</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Account Meta & Quick Actions */}
        <div className="md:col-span-4 space-y-6">
          {/* Account Privileges */}
          <div className="glass rounded-3xl p-6 border border-line">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-accent" />
              <h3 className="text-sm font-bold text-fg font-['Outfit']">Account Privileges</h3>
            </div>
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
              <div className="flex items-center gap-3 text-xs text-fg-muted">
                <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
                <span>AI financial assistant chat</span>
              </div>
              {user?.role === 'admin' ? (
                <div className="flex items-center gap-3 text-xs text-accent font-semibold pt-1 border-t border-line/60">
                  <Shield className="h-4 w-4 shrink-0" />
                  <span>Full Administrative Access</span>
                </div>
              ) : null}
            </div>
          </div>

          {/* Student Financial Tip */}
          <div className="rounded-3xl border border-accent/20 bg-accent-soft/30 p-5 backdrop-blur-md">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Student Tip</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-fg-muted">
              Keeping your Monthly Income up-to-date allows BudgetBuddy to calculate your accurate Safe Daily Spending Limit so you never run dry before semester-end.
            </p>
          </div>

          {/* Danger Zone / Session Logout */}
          <div className="glass rounded-3xl p-5 border border-line">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-fg">Session Management</div>
                <div className="text-[11px] text-fg-muted mt-0.5">End active authentication session</div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-danger/30 bg-danger-soft/40 px-3 py-1.5 text-xs font-semibold text-danger hover:bg-danger-soft/70 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
