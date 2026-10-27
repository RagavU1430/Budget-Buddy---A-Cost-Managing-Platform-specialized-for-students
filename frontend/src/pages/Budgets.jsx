import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Plus, Target } from 'lucide-react'

import { createBudget, getBudgets } from '../api/budgets'
import { getExpenses } from '../api/expenses'
import { formatCurrency, getCurrentMonthFirstDay } from '../utils/format'
import ProgressBar from '../components/ProgressBar'
import Modal from '../components/Modal'
import FormField, { inputClass } from '../components/FormField'
import { SkeletonCard } from '../components/Skeleton'
import { EXPENSE_CATEGORIES, categoryMeta, toneClasses } from '../utils/categories'

export default function Budgets() {
  const [budgets, setBudgets] = useState([])
  const [expenses, setExpenses] = useState([])
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ category: 'food', limit_amount: '', month: getCurrentMonthFirstDay() })
  const [loading, setLoading] = useState(true)

  const normalize = (data) => {
    if (Array.isArray(data)) return data
    if (data && Array.isArray(data.results)) return data.results
    return []
  }

  const loadData = async () => {
    try {
      const [budRes, expRes] = await Promise.all([getBudgets(), getExpenses()])
      setBudgets(normalize(budRes.data))
      setExpenses(normalize(expRes.data))
    } catch {
      // ignore — empty state will render
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const dayOfMonth = now.getDate()
  const remainingDays = Math.max(1, daysInMonth - dayOfMonth + 1)

  const spentByCategory = useMemo(() => {
    const map = {}
    expenses
      .filter((e) => e?.date && new Date(e.date) >= monthStart)
      .forEach((e) => {
        if (e.category) map[e.category] = (map[e.category] || 0) + Number(e.amount || 0)
      })
    return map
  }, [expenses])

  const totalBudget = budgets.reduce((sum, b) => sum + Number(b.limit_amount || 0), 0)
  const totalSpent = Object.values(spentByCategory).reduce((sum, v) => sum + v, 0)
  const totalRemaining = totalBudget - totalSpent
  const perDay = totalRemaining / remainingDays
  const overallUtil = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    await createBudget({ ...form, limit_amount: Number(form.limit_amount) })
    setModalOpen(false)
    setForm({ category: 'food', limit_amount: '', month: getCurrentMonthFirstDay() })
    loadData()
  }

  const summary = [
    { label: 'Monthly Budget', value: formatCurrency(totalBudget), tone: 'text-fg' },
    { label: 'Spent So Far', value: formatCurrency(totalSpent), tone: 'text-fg' },
    {
      label: 'Remaining Safe-to-Spend',
      value: formatCurrency(totalRemaining),
      tone: totalRemaining >= 0 ? 'text-accent' : 'text-danger',
    },
    { label: 'Remaining per Day', value: formatCurrency(perDay), tone: 'text-fg' },
  ]

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="label text-accent">Budgets</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Budget Management Hub</h1>
          <p className="mt-1 text-sm text-fg-muted">Category allocations with smart utilization alerts for student spending.</p>
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="cursor-pointer shrink-0 self-start rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-on-accent shadow-[var(--shadow-glow)] transition-transform duration-200 hover:scale-[1.03] active:scale-[0.98] sm:self-auto"
        >
          <span className="flex items-center gap-2">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Category Budget
          </span>
        </button>
      </header>

      {/* Summary strip */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Budget summary">
        {summary.map((s, i) => (
          <article
            key={s.label}
            className="glass rounded-[var(--radius-card)] p-5 animate-[rise_0.5s_cubic-bezier(0.22,1,0.36,1)_both]"
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <p className="label">{s.label}</p>
            <p className={`data mt-2.5 text-2xl font-semibold ${s.tone}`}>{s.value}</p>
          </article>
        ))}
      </section>

      {/* Overall utilization bar */}
      {totalBudget > 0 ? (
        <section className="glass rounded-[var(--radius-card)] p-5" aria-label="Overall budget utilization">
          <ProgressBar value={overallUtil} label="Overall Utilization" />
        </section>
      ) : null}

      {totalBudget > 0 && overallUtil >= 75 ? (
        <div
          className={`flex items-center gap-3 rounded-2xl border px-5 py-3.5 text-sm ${
            overallUtil >= 100
              ? 'border-danger/30 bg-danger-soft text-danger'
              : 'border-warn/30 bg-warn-soft text-warn'
          }`}
          role="alert"
        >
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          {overallUtil >= 100
            ? 'You are over budget. Consider cutting discretionary spend.'
            : 'You are on track to exhaust your budget before month-end.'}
        </div>
      ) : null}

      {/* Budget cards */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Category budgets">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : budgets.length === 0 ? (
          <div className="md:col-span-2 xl:col-span-3">
            <div className="glass flex flex-col items-center justify-center rounded-[var(--radius-card)] border-dashed px-6 py-12 text-center">
              <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 ring-1 ring-line" aria-hidden="true">
                <Target className="h-6 w-6 text-fg-faint" />
              </span>
              <h3 className="text-base font-semibold text-fg">No budgets set</h3>
              <p className="mt-1.5 text-sm text-fg-muted">Create category budgets to track utilization and get alerts.</p>
            </div>
          </div>
        ) : (
          budgets.map((budget, i) => {
            const spent = spentByCategory[budget.category] || 0
            const limit = Number(budget.limit_amount || 0)
            const util = limit > 0 ? (spent / limit) * 100 : 0
            const meta = categoryMeta(budget.category)
            const Icon = meta?.icon ?? Target
            return (
              <article
                key={budget.id}
                className="glass rounded-[var(--radius-card)] p-5 transition-transform duration-200 hover:-translate-y-0.5 animate-[rise_0.5s_cubic-bezier(0.22,1,0.36,1)_both]"
                style={{ animationDelay: `${i * 70}ms` }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ${
                        toneClasses[meta?.tone] ?? toneClasses.neutral
                      }`}
                      aria-hidden="true"
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-fg">{meta?.label ?? budget.category}</p>
                      <p className="text-xs text-fg-faint">Month: {budget.month}</p>
                    </div>
                  </div>
                  <span
                    className={`data shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                      util >= 100 ? 'bg-danger-soft text-danger' : util >= 75 ? 'bg-warn-soft text-warn' : 'bg-accent-soft text-accent'
                    }`}
                  >
                    {util.toFixed(0)}%
                  </span>
                </div>
                <dl className="mt-4 space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="text-fg-muted">Limit</dt>
                    <dd className="data text-fg">{formatCurrency(limit)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-fg-muted">Spent</dt>
                    <dd className="data text-fg">{formatCurrency(spent)}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="text-fg-muted">Remaining</dt>
                    <dd className={`data ${limit - spent >= 0 ? 'text-accent' : 'text-danger'}`}>{formatCurrency(limit - spent)}</dd>
                  </div>
                </dl>
                <div className="mt-4">
                  <ProgressBar value={util} />
                </div>
              </article>
            )
          })
        )}
      </section>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Monthly Budget Allocator" subtitle="Set a spending limit for one category">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FormField label="Category" id="budget-category">
            <select
              id="budget-category"
              value={form.category}
              onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
              className={`${inputClass} cursor-pointer`}
            >
              {EXPENSE_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value} className="bg-surface text-fg">
                  {cat.label}
                </option>
              ))}
            </select>
          </FormField>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Month" id="budget-month">
              <input
                id="budget-month"
                type="date"
                value={form.month}
                onChange={(e) => setForm((prev) => ({ ...prev, month: e.target.value }))}
                className={inputClass}
              />
            </FormField>
            <FormField label="Limit Amount" id="budget-limit">
              <div className="flex items-center gap-2 rounded-xl border border-line bg-white/4 px-3.5 py-2.5 transition-colors duration-200 focus-within:border-accent/60">
                <span className="text-sm text-fg-faint" aria-hidden="true">₹</span>
                <input
                  id="budget-limit"
                  type="number"
                  step="0.01"
                  min="1"
                  value={form.limit_amount}
                  onChange={(e) => setForm((prev) => ({ ...prev, limit_amount: e.target.value }))}
                  className="data w-full bg-transparent text-sm text-fg placeholder:text-fg-faint outline-none"
                  placeholder="5000"
                  required
                />
              </div>
            </FormField>
          </div>
          <button
            type="submit"
            className="mt-2 w-full cursor-pointer rounded-full bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent shadow-[var(--shadow-glow)] transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98]"
          >
            Save Budget
          </button>
        </form>
      </Modal>
    </div>
  )
}
