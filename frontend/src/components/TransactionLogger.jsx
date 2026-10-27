import { useState } from 'react'
import { CalendarDays, PlusCircle, ReceiptText } from 'lucide-react'

import { createExpense } from '../api/expenses'
import { createIncome } from '../api/incomes'
import Modal from './Modal'
import Alert from './Alert'
import { inputClass } from './FormField'
import { EXPENSE_CATEGORIES, INCOME_SOURCES, PAYMENT_METHODS, toneClasses } from '../utils/categories'

const today = new Date().toISOString().slice(0, 10)
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)

const chipClass = (active, tone) =>
  `cursor-pointer rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors duration-200 ${
    active
      ? tone === 'green'
        ? 'border-accent/50 bg-accent-soft text-fg'
        : 'border-danger/50 bg-danger-soft text-fg'
      : 'border-line bg-white/4 text-fg-muted hover:bg-white/8 hover:text-fg'
  }`

export default function TransactionLogger({ open, onClose, onSuccess }) {
  const [tab, setTab] = useState('expense')
  const [expenseForm, setExpenseForm] = useState({
    title: '',
    amount: '',
    category: 'food',
    payment_method: 'upi',
    date: today,
    notes: '',
  })
  const [incomeForm, setIncomeForm] = useState({
    title: '',
    amount: '',
    source_type: 'pocket_money',
    date: today,
    notes: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleExpenseChange = (e) => setExpenseForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  const handleIncomeChange = (e) => setIncomeForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (tab === 'expense') {
        await createExpense({ ...expenseForm, amount: Number(expenseForm.amount) })
      } else {
        await createIncome({ ...incomeForm, amount: Number(incomeForm.amount) })
      }
      onSuccess?.()
      onClose?.()
      setExpenseForm({ title: '', amount: '', category: 'food', payment_method: 'upi', date: today, notes: '' })
      setIncomeForm({ title: '', amount: '', source_type: 'pocket_money', date: today, notes: '' })
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to log transaction')
    } finally {
      setLoading(false)
    }
  }

  const isExpense = tab === 'expense'

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isExpense ? 'Log an Expense' : 'Add Income'}
      subtitle={isExpense ? 'Track where your money goes' : 'Record money coming in'}
    >
      {/* Segmented mode switch */}
      <div
        className="mb-5 grid grid-cols-2 rounded-full border border-line bg-white/4 p-1 text-sm"
        role="tablist"
        aria-label="Transaction type"
      >
        <button
          type="button"
          role="tab"
          aria-selected={isExpense}
          onClick={() => setTab('expense')}
          className={`flex cursor-pointer items-center justify-center gap-2 rounded-full px-4 py-2.5 font-medium transition-colors duration-200 ${
            isExpense ? 'bg-danger-soft text-fg shadow-[inset_0_0_0_1px_rgba(239,68,68,0.35)]' : 'text-fg-muted hover:text-fg'
          }`}
        >
          <ReceiptText className={`h-4 w-4 ${isExpense ? 'text-danger' : ''}`} aria-hidden="true" />
          Log Expense
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={!isExpense}
          onClick={() => setTab('income')}
          className={`flex cursor-pointer items-center justify-center gap-2 rounded-full px-4 py-2.5 font-medium transition-colors duration-200 ${
            !isExpense ? 'bg-accent-soft text-fg shadow-[inset_0_0_0_1px_rgba(34,197,94,0.35)]' : 'text-fg-muted hover:text-fg'
          }`}
        >
          <PlusCircle className={`h-4 w-4 ${!isExpense ? 'text-accent' : ''}`} aria-hidden="true" />
          Add Income
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Amount */}
        <div>
          <label htmlFor="tx-amount" className="label">
            Amount
          </label>
          <div className="mt-2 flex items-center gap-2 rounded-2xl border border-line bg-white/4 px-4 py-3 transition-colors duration-200 focus-within:border-accent/60">
            <span className="text-lg text-fg-faint" aria-hidden="true">₹</span>
            <input
              id="tx-amount"
              name="amount"
              value={isExpense ? expenseForm.amount : incomeForm.amount}
              onChange={isExpense ? handleExpenseChange : handleIncomeChange}
              type="number"
              step="0.01"
              min="1"
              placeholder="0.00"
              className="data w-full bg-transparent text-2xl font-semibold text-fg placeholder:text-fg-faint outline-none"
              required
            />
          </div>
        </div>

        {isExpense ? (
          <>
            {/* Category picker */}
            <div>
              <span className="label" id="category-label">Category</span>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3" role="group" aria-labelledby="category-label">
                {EXPENSE_CATEGORIES.map((cat) => {
                  const active = expenseForm.category === cat.value
                  return (
                    <button
                      type="button"
                      key={cat.value}
                      aria-pressed={active}
                      onClick={() => setExpenseForm((prev) => ({ ...prev, category: cat.value }))}
                      className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm font-medium transition-colors duration-200 ${
                        active
                          ? 'border-danger/50 bg-danger-soft text-fg'
                          : 'border-line bg-white/4 text-fg-muted hover:bg-white/8 hover:text-fg'
                      }`}
                    >
                      <span
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ring-1 ${toneClasses[cat.tone]}`}
                        aria-hidden="true"
                      >
                        <cat.icon className="h-3.5 w-3.5" />
                      </span>
                      <span className="truncate">{cat.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Payment method */}
            <div>
              <span className="label" id="payment-label">Payment Method</span>
              <div className="mt-2 flex flex-wrap gap-2" role="group" aria-labelledby="payment-label">
                {PAYMENT_METHODS.map((pm) => (
                  <button
                    type="button"
                    key={pm.value}
                    aria-pressed={expenseForm.payment_method === pm.value}
                    onClick={() => setExpenseForm((prev) => ({ ...prev, payment_method: pm.value }))}
                    className={chipClass(expenseForm.payment_method === pm.value, 'danger')}
                  >
                    {pm.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="expense-date" className="label">Date</label>
                <div className="mt-2 flex items-center gap-2 rounded-xl border border-line bg-white/4 px-3 py-2.5 transition-colors duration-200 focus-within:border-accent/60">
                  <CalendarDays className="h-4 w-4 shrink-0 text-fg-faint" aria-hidden="true" />
                  <input
                    id="expense-date"
                    name="date"
                    type="date"
                    value={expenseForm.date}
                    onChange={handleExpenseChange}
                    className="w-full bg-transparent text-sm text-fg outline-none"
                  />
                </div>
                <div className="mt-2 flex gap-1.5">
                  <button
                    type="button"
                    onClick={() => setExpenseForm((prev) => ({ ...prev, date: today }))}
                    className={`cursor-pointer text-xs font-medium transition-colors duration-200 ${expenseForm.date === today ? 'text-accent' : 'text-fg-faint hover:text-fg-muted'}`}
                  >
                    Today
                  </button>
                  <span className="text-xs text-fg-faint" aria-hidden="true">·</span>
                  <button
                    type="button"
                    onClick={() => setExpenseForm((prev) => ({ ...prev, date: yesterday }))}
                    className={`cursor-pointer text-xs font-medium transition-colors duration-200 ${expenseForm.date === yesterday ? 'text-accent' : 'text-fg-faint hover:text-fg-muted'}`}
                  >
                    Yesterday
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="expense-title" className="label">Merchant / Title</label>
                <input
                  id="expense-title"
                  name="title"
                  value={expenseForm.title}
                  onChange={handleExpenseChange}
                  placeholder="Campus Canteen Lunch"
                  className={`${inputClass} mt-2`}
                  required
                />
              </div>
            </div>
            <textarea
              name="notes"
              value={expenseForm.notes}
              onChange={handleExpenseChange}
              placeholder="Add a note (optional)"
              aria-label="Notes"
              className={`${inputClass} min-h-[80px] resize-y`}
            />
          </>
        ) : (
          <>
            {/* Income source */}
            <div>
              <span className="label" id="source-label">Source Type</span>
              <div className="mt-2 flex flex-wrap gap-2" role="group" aria-labelledby="source-label">
                {INCOME_SOURCES.map((src) => (
                  <button
                    type="button"
                    key={src.value}
                    aria-pressed={incomeForm.source_type === src.value}
                    onClick={() => setIncomeForm((prev) => ({ ...prev, source_type: src.value }))}
                    className={chipClass(incomeForm.source_type === src.value, 'green')}
                  >
                    {src.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="income-date" className="label">Date</label>
                <div className="mt-2 flex items-center gap-2 rounded-xl border border-line bg-white/4 px-3 py-2.5 transition-colors duration-200 focus-within:border-accent/60">
                  <CalendarDays className="h-4 w-4 shrink-0 text-fg-faint" aria-hidden="true" />
                  <input
                    id="income-date"
                    name="date"
                    type="date"
                    value={incomeForm.date}
                    onChange={handleIncomeChange}
                    className="w-full bg-transparent text-sm text-fg outline-none"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="income-title" className="label">Title / Depositor</label>
                <input
                  id="income-title"
                  name="title"
                  value={incomeForm.title}
                  onChange={handleIncomeChange}
                  placeholder="Monthly pocket money"
                  className={`${inputClass} mt-2`}
                  required
                />
              </div>
            </div>
            <textarea
              name="notes"
              value={incomeForm.notes}
              onChange={handleIncomeChange}
              placeholder="Add a note (optional)"
              aria-label="Notes"
              className={`${inputClass} min-h-[80px] resize-y`}
            />
          </>
        )}

        <Alert message={error} type="error" />

        <button
          type="submit"
          disabled={loading}
          className="mt-1 w-full cursor-pointer rounded-full bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent shadow-[var(--shadow-glow)] transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:scale-100 disabled:opacity-60"
        >
          {loading ? 'Saving…' : isExpense ? 'Log Expense' : 'Add Income'}
        </button>
      </form>
    </Modal>
  )
}
