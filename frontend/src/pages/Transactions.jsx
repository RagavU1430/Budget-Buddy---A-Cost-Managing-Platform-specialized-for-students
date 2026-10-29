import { useEffect, useMemo, useState } from 'react'
import { Calendar, Filter, Receipt, Search, Trash2, Zap } from 'lucide-react'

import { deleteExpense, getExpenses } from '../api/expenses'
import { deleteIncome, getIncomes } from '../api/incomes'
import { formatCurrency } from '../utils/format'
import DropdownSelect from '../components/DropdownSelect'
import EmptyState from '../components/EmptyState'
import Badge from '../components/Badge'
import Modal from '../components/Modal'
import { SkeletonList } from '../components/Skeleton'
import { EXPENSE_CATEGORIES, PAYMENT_METHODS, categoryMeta, toneClasses } from '../utils/categories'

const categoryOptions = [{ value: 'all', label: 'All Categories' }, ...EXPENSE_CATEGORIES]
const paymentOptions = [{ value: 'all', label: 'All Methods' }, ...PAYMENT_METHODS]

const rangeOptions = [
  { value: 'all', label: 'All Time' },
  { value: 'this', label: 'This Month' },
  { value: 'last', label: 'Last Month' },
]

export default function Transactions() {
  const [expenses, setExpenses] = useState([])
  const [incomes, setIncomes] = useState([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [payment, setPayment] = useState('all')
  const [range, setRange] = useState('this')
  const [loading, setLoading] = useState(true)
  const [deleteItem, setDeleteItem] = useState(null)

  const normalize = (data) => {
    if (Array.isArray(data)) return data
    if (data && Array.isArray(data.results)) return data.results
    return []
  }

  const loadData = async () => {
    try {
      const [expRes, incRes] = await Promise.all([getExpenses(), getIncomes()])
      setExpenses(normalize(expRes.data))
      setIncomes(normalize(incRes.data))
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
  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0)

  const merged = useMemo(() => {
    const items = [
      ...expenses.map((e) => ({ ...e, type: 'expense' })),
      ...incomes.map((i) => ({ ...i, type: 'income' })),
    ]

    return items
      .filter((item) => {
        if (range === 'this') return new Date(item.date) >= thisMonthStart
        if (range === 'last') {
          const d = new Date(item.date)
          return d >= lastMonthStart && d <= lastMonthEnd
        }
        return true
      })
      .filter((item) => {
        if (category !== 'all') {
          if (item.type === 'expense') return item.category === category
          return false
        }
        return true
      })
      .filter((item) => {
        if (payment !== 'all') {
          if (item.type === 'expense') return item.payment_method === payment
          return false
        }
        return true
      })
      .filter((item) => {
        if (!search) return true
        const term = search.toLowerCase()
        return (item.title || '').toLowerCase().includes(term) || (item.notes || '').toLowerCase().includes(term)
      })
      .sort((a, b) => new Date(b.date) - new Date(a.date) || b.id - a.id)
  }, [expenses, incomes, search, category, payment, range])

  const grouped = useMemo(() => {
    const groups = {}
    merged.forEach((item) => {
      const label = item.date === now.toISOString().slice(0, 10) ? 'Today' : item.date
      if (!groups[label]) groups[label] = []
      groups[label].push(item)
    })
    return groups
  }, [merged])

  const filterCount = [category !== 'all', payment !== 'all', range !== 'all', Boolean(search)].filter(Boolean).length

  const handleDelete = async () => {
    if (!deleteItem) return
    try {
      if (deleteItem.type === 'expense') await deleteExpense(deleteItem.id)
      else await deleteIncome(deleteItem.id)
      await loadData()
    } finally {
      setDeleteItem(null)
    }
  }

  const clearFilters = () => {
    setSearch('')
    setCategory('all')
    setPayment('all')
    setRange('all')
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="label text-accent">Transactions</p>
        <h1 className="text-3xl font-bold tracking-tight">History</h1>
        <p className="text-sm text-fg-muted">Search, filter, and manage every income and expense in one place.</p>
      </header>

      {/* Filter bar */}
      <section className="glass relative z-30 rounded-[var(--radius-card)] p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative w-full lg:max-w-md">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-faint" aria-hidden="true" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title or note"
              aria-label="Search transactions"
              className="w-full rounded-full border border-line bg-white/4 py-2.5 pl-10 pr-4 text-sm text-fg placeholder:text-fg-faint outline-none transition-colors duration-200 focus:border-accent/60"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <DropdownSelect
              value={range}
              onChange={setRange}
              options={rangeOptions}
              icon={Calendar}
              ariaLabel="Date range"
            />
            <DropdownSelect
              value={category}
              onChange={setCategory}
              options={categoryOptions}
              icon={Filter}
              ariaLabel="Category"
            />
            <DropdownSelect
              value={payment}
              onChange={setPayment}
              options={paymentOptions}
              ariaLabel="Payment method"
            />
            {filterCount > 0 ? (
              <button
                type="button"
                onClick={clearFilters}
                className="cursor-pointer rounded-full border border-line bg-white/4 px-3.5 py-2 text-xs font-medium text-fg-muted transition-colors duration-200 hover:border-danger/40 hover:text-danger"
              >
                Clear ({filterCount})
              </button>
            ) : null}
          </div>
        </div>
        {!loading && merged.length > 0 ? (
          <p className="mt-3 text-xs text-fg-faint" role="status">
            <span className="data text-fg-muted">{merged.length}</span> record{merged.length === 1 ? '' : 's'} found
          </p>
        ) : null}
      </section>

      {/* Grouped history */}
      <section className="relative z-10 flex flex-col gap-6" aria-label="Transaction history">
        {loading ? (
          <div className="glass overflow-hidden rounded-[var(--radius-card)]">
            <SkeletonList count={6} label="Loading history" />
          </div>
        ) : merged.length === 0 ? (
          <EmptyState
            icon={Receipt}
            title="No records found"
            description="Try adjusting the filters, or log your first transaction from the dashboard."
          />
        ) : (
          Object.entries(grouped).map(([label, items], gi) => (
            <div
              key={label}
              className="glass overflow-hidden rounded-[var(--radius-card)] animate-[rise_0.45s_cubic-bezier(0.22,1,0.36,1)_both]"
              style={{ animationDelay: `${gi * 60}ms` }}
            >
              <div className="border-b border-line px-6 py-3">
                <h2 className="label text-fg-muted">{label}</h2>
              </div>
              <div className="divide-y divide-line">
                {items.map((item) => {
                  const isExpense = item.type === 'expense'
                  const meta = isExpense ? categoryMeta(item.category) : null
                  const Icon = meta?.icon ?? Zap
                  const amount = Number(item.amount || 0)
                  return (
                    <div
                      key={`${item.type}-${item.id}`}
                      className="flex flex-col gap-3 px-6 py-4 transition-colors duration-150 hover:bg-white/[0.03] sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ring-1 ${
                            isExpense ? toneClasses[meta?.tone] ?? toneClasses.neutral : toneClasses.green
                          }`}
                          aria-hidden="true"
                        >
                          <Icon className="h-4.5 w-4.5" />
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-fg">{item.title}</p>
                          <p className="truncate text-xs text-fg-faint">
                            {isExpense
                              ? `${meta?.label ?? item.category} · ${item.payment_method?.toUpperCase()}`
                              : `Income · ${item.source_type?.replace('_', ' ')}`}
                            {item.notes ? ` · ${item.notes}` : ''}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between gap-4 sm:justify-end">
                        <div className="text-right">
                          <p className={`data text-sm font-semibold ${isExpense ? 'text-danger' : 'text-accent'}`}>
                            {isExpense ? '−' : '+'}
                            {formatCurrency(amount)}
                          </p>
                          <Badge tone={isExpense ? 'rose' : 'green'}>{isExpense ? 'Expense' : 'Income'}</Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setDeleteItem(item)}
                            aria-label={`Delete ${item.title}`}
                            className="cursor-pointer rounded-full border border-line bg-white/4 p-2 text-fg-muted transition-colors duration-200 hover:border-danger/40 hover:bg-danger-soft hover:text-danger"
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))
        )}
      </section>

      <Modal open={Boolean(deleteItem)} onClose={() => setDeleteItem(null)} title="Delete transaction">
        <p className="text-sm text-fg-muted">
          Delete <span className="font-medium text-fg">"{deleteItem?.title}"</span>? This action cannot be undone.
        </p>
        <div className="mt-6 flex gap-2">
          <button
            type="button"
            onClick={() => setDeleteItem(null)}
            className="flex-1 cursor-pointer rounded-full border border-line bg-white/4 px-4 py-2.5 text-sm font-medium text-fg-muted transition-colors duration-200 hover:bg-white/8 hover:text-fg"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="flex-1 cursor-pointer rounded-full bg-danger px-4 py-2.5 text-sm font-semibold text-white transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98]"
          >
            Delete
          </button>
        </div>
      </Modal>
    </div>
  )
}
