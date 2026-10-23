import { useEffect, useState } from 'react'

import Alert from '../components/Alert.jsx'
import FormField from '../components/FormField.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { formatError } from '../utils/errors.js'

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
      setStatus({ message: 'Profile updated.', type: 'success' })
    } catch (err) {
      setStatus({ message: formatError(err), type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100'

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-bold text-slate-900">Profile</h1>
      <p className="mt-1 text-sm text-slate-500">
        Signed in as {user?.email} ({user?.role})
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-6"
      >
        <Alert message={status.message} type={status.type} />

        <FormField label="Phone" id="phone">
          <input
            id="phone"
            name="phone"
            className={inputClass}
            value={form.phone}
            onChange={handleChange}
          />
        </FormField>

        <FormField label="Monthly income" id="monthly_income">
          <input
            id="monthly_income"
            name="monthly_income"
            type="number"
            min="0"
            step="0.01"
            className={inputClass}
            value={form.monthly_income}
            onChange={handleChange}
          />
        </FormField>

        <FormField label="Currency" id="currency">
          <input
            id="currency"
            name="currency"
            maxLength={3}
            className={inputClass}
            value={form.currency}
            onChange={handleChange}
          />
        </FormField>

        <button
          type="submit"
          disabled={saving}
          className="self-start rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </div>
  )
}
