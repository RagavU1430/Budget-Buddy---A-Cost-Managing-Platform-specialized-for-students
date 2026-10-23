import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Alert from '../components/Alert.jsx'
import FormField from '../components/FormField.jsx'
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

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
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

  const inputClass =
    'rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100'

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">
          Create your <span className="text-emerald-600">BudgetBuddy</span> account
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          New accounts start with the student role. Premium access is granted by an admin.
        </p>

        <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
          <Alert message={error} />

          <div className="grid grid-cols-2 gap-3">
            <FormField label="First name" id="first_name">
              <input
                id="first_name"
                name="first_name"
                className={inputClass}
                value={form.first_name}
                onChange={handleChange}
              />
            </FormField>
            <FormField label="Last name" id="last_name">
              <input
                id="last_name"
                name="last_name"
                className={inputClass}
                value={form.last_name}
                onChange={handleChange}
              />
            </FormField>
          </div>

          <FormField label="Email" id="email">
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              className={inputClass}
              value={form.email}
              onChange={handleChange}
            />
          </FormField>

          <FormField label="Username" id="username">
            <input
              id="username"
              name="username"
              required
              autoComplete="username"
              className={inputClass}
              value={form.username}
              onChange={handleChange}
            />
          </FormField>

          <FormField label="Account Role" id="role">
            <select
              id="role"
              name="role"
              className={inputClass}
              value={form.role}
              onChange={handleChange}
            >
              <option value="student">Student (Standard)</option>
              <option value="premium">Premium User (Advanced features)</option>
            </select>
          </FormField>

          <FormField label="Password" id="password">
            <input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="new-password"
              className={inputClass}
              value={form.password}
              onChange={handleChange}
            />
          </FormField>

          <FormField label="Confirm password" id="password_confirm">
            <input
              id="password_confirm"
              name="password_confirm"
              type="password"
              required
              autoComplete="new-password"
              className={inputClass}
              value={form.password_confirm}
              onChange={handleChange}
            />
          </FormField>

          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
          >
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-600">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-emerald-700 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
