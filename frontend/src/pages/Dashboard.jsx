import { useEffect, useMemo, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, Plus, Receipt, Wallet, Zap } from 'lucide-react'

import { getBudgets } from '../api/budgets'
import { getExpenses } from '../api/expenses'
import { getIncomes } from '../api/incomes'
import Badge from '../components/Badge'
import BudgetGauge from '../components/BudgetGauge'
import ProgressBar from '../components/ProgressBar'
import StatCard from '../components/StatCard'
import TransactionLogger from '../components/TransactionLogger'
import { SkeletonCard, SkeletonList } from '../components/Skeleton'
import { useAuth } from '../context/AuthContext.jsx'
import { categoryMeta, toneClasses } from '../utils/categories'
import { formatCurrency } from '../utils/format'

const normalize = (data) => {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

export default function Dashboard() {
  const { user } = useAuth()
  const [expenses, setExpenses] = useState([])
  const [incomes, setIncomes] = useState([])
  const [budgets, setBudgets] = useState([])
  const [loggerOpen, setLoggerOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    try {
      const [expRes, incRes, budRes] = await Promise.all([getExpenses(), getIncomes(), getBudgets()])
      setExpenses(normalize(expRes.data))
      setIncomes(normalize(incRes.data))
      setBudgets(normalize(budRes.data))
    } catch {
      // keep empty state on failure
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
  const daysRemaining = Math.max(1, daysInMonth - dayOfMonth + 1)

  const { totalExpense, totalIncome, totalBudget, recent } = useMemo(() => {
    const monthExpenses = expenses.filter((e) => e?.date && new Date(e.date) >= monthStart)
    const monthIncomes = incomes.filter((i) => i?.date && new Date(i.date) >= monthStart)
    const exp = monthExpenses.reduce((sum, e) => sum + Number(e.amount || 0), 0)
    const inc = monthIncomes.reduce((sum, i) => sum + Number(i.amount || 0), 0)
    const bud = budgets.reduce((sum, b) => sum + Number(b.limit_amount || 0), 0)
    const recentTx = [...expenses, ...incomes]
      .sort((a, b) => {
        const d = new Date(b?.date || 0) - new Date(a?.date || 0)
        return d !== 0 ? d : (b?.id || 0) - (a?.id || 0)
      })
      .slice(0, 6)
    return { totalExpense: exp, totalIncome: inc, totalBudget: bud, recent: recentTx }
  }, [expenses, incomes, budgets])

  const netBalance = totalIncome - totalExpense
  const budgetUtil = totalBudget > 0 ? (totalExpense / totalBudget) * 100 : 0
  const dailyAvg = dayOfMonth > 0 ? totalExpense / dayOfMonth : 0
  const safePerDay = totalBudget > 0 ? Math.max(0, (totalBudget - totalExpense) / daysRemaining) : 0

  return (
    <div className="flex flex-col gap-6">
      {/* Hero */}
      <section className="glass-strong relative overflow-hidden rounded-[var(--radius-card)] p-7 sm:p-9">
        <div className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-accent/10 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-32 left-8 h-72 w-72 rounded-full bg-info/10 blur-3xl" aria-hidden="true" />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="label text-accent">Overview</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
              Welcome back{user?.first_name ? `, ${user.first_name}` : ''}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-fg-muted">
              Your neo-fintech command center — pocket money, campus spend, and budgets, all in real time.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={() => setLoggerOpen(true)}
              className="cursor-pointer rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-on-accent shadow-[var(--shadow-glow)] transition-transform duration-200 hover:scale-[1.03] active:scale-[0.98]"
            >
              <span className="flex items-center gap-2">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Log Expense
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Stat cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Monthly summary">
        <StatCard
          title="Net Disposable Balance"
          value={formatCurrency(netBalance)}
          icon={Wallet}
          trend={netBalance >= 0 ? `Safe to spend ${formatCurrency(safePerDay)}/day` : 'Tight this month'}
          tone={netBalance >= 0 ? 'green' : 'rose'}
          delay={0}
        />
        <StatCard
          title="Total Monthly Income"
          value={formatCurrency(totalIncome)}
          icon={ArrowUpRight}
          trend={`${incomes.filter((i) => i?.date && new Date(i.date) >= monthStart).length} deposits this month`}
          tone="green"
          delay={70}
        />
        <StatCard
          title="Total Monthly Expenses"
          value={formatCurrency(totalExpense)}
          icon={ArrowDownRight}
          trend={`Avg ${formatCurrency(dailyAvg)}/day`}
          tone="rose"
          delay={140}
        />
        {loading ? (
          <SkeletonCard />
        ) : (
          <article
            className={`glass relative overflow-hidden rounded-[var(--radius-card)] p-5 animate-[rise_0.5s_cubic-bezier(0.22,1,0.36,1)_both] transition-transform duration-200 hover:-translate-y-0.5`}
            style={{ animationDelay: '210ms' }}
          >
            <div className="flex items-center justify-between mb-1">
              <p className="label">Budget Utilization</p>
              {budgetUtil >= 100 ? (
                <span className="rounded-full bg-danger-soft px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-danger animate-[pulse-ring_1.6s_ease-in-out_infinite]">
                  Over
                </span>
              ) : null}
            </div>
            <BudgetGauge value={budgetUtil} spent={totalExpense} limit={totalBudget} />
          </article>
        )}
      </section>

      {/* Transactions + side panel */}
      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="glass overflow-hidden rounded-[var(--radius-card)]">
          <div className="flex items-center justify-between border-b border-line px-6 py-4">
            <div>
              <h2 className="text-base font-semibold tracking-tight text-fg">Recent Transactions</h2>
              <p className="text-xs text-fg-muted">Latest activity across income & expenses</p>
            </div>
            <button
              type="button"
              onClick={() => setLoggerOpen(true)}
              className="cursor-pointer rounded-full border border-line bg-white/5 px-3.5 py-1.5 text-xs font-medium text-fg-muted transition-colors duration-200 hover:border-accent/40 hover:text-fg"
            >
              + Add
            </button>
          </div>
          <div className="divide-y divide-line">
            {loading ? (
              <SkeletonList count={5} label="Loading transactions" />
            ) : recent.length === 0 ? (
              <div className="px-6 py-10 text-center">
                <Receipt className="mx-auto h-8 w-8 text-fg-faint" aria-hidden="true" />
                <p className="mt-3 text-sm text-fg-muted">No transactions yet.</p>
                <p className="mt-1 text-xs text-fg-faint">Log your first expense to see it here.</p>
              </div>
            ) : (
              recent.map((tx, i) => {
                const isExpense = 'category' in tx
                const meta = isExpense ? categoryMeta(tx.category) : null
                const Icon = meta?.icon ?? Zap
                const amount = Number(tx.amount || 0)
                return (
                  <div
                    key={`${isExpense ? 'exp' : 'inc'}-${tx.id}`}
                    className="flex items-center justify-between gap-3 px-6 py-3.5 transition-colors duration-150 hover:bg-white/[0.03] animate-[rise_0.4s_cubic-bezier(0.22,1,0.36,1)_both]"
                    style={{ animationDelay: `${i * 45}ms` }}
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
                        <p className="truncate text-sm font-medium text-fg">{tx.title || (isExpense ? meta?.label : 'Income')}</p>
                        <p className="truncate text-xs text-fg-faint">
                          {tx.date}
                          {isExpense ? ` · ${tx.payment_method?.toUpperCase()}` : ` · ${tx.source_type?.replace('_', ' ')}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <p className={`data text-sm font-semibold ${isExpense ? 'text-danger' : 'text-accent'}`}>
                        {isExpense ? '−' : '+'}
                        {formatCurrency(amount)}
                      </p>
                      <Badge tone={isExpense ? 'rose' : 'green'}>{isExpense ? 'Expense' : 'Income'}</Badge>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          {/* Quick actions */}
          <div className="glass rounded-[var(--radius-card)] p-5">
            <h3 className="text-sm font-semibold tracking-tight text-fg">Quick Actions</h3>
            <p className="mt-0.5 text-xs text-fg-muted">One-tap logging</p>
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setLoggerOpen(true)}
                className="cursor-pointer flex items-center justify-between rounded-2xl border border-danger/25 bg-danger-soft px-4 py-3 text-sm font-medium text-fg transition-colors duration-200 hover:border-danger/50"
              >
                <span className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-danger/20" aria-hidden="true">
                    <ArrowDownRight className="h-4 w-4 text-danger" />
                  </span>
                  Log Expense
                </span>
                <Plus className="h-4 w-4 text-fg-faint" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => setLoggerOpen(true)}
                className="cursor-pointer flex items-center justify-between rounded-2xl border border-accent/25 bg-accent-soft px-4 py-3 text-sm font-medium text-fg transition-colors duration-200 hover:border-accent/50"
              >
                <span className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/20" aria-hidden="true">
                    <ArrowUpRight className="h-4 w-4 text-accent" />
                  </span>
                  Add Income
                </span>
                <Plus className="h-4 w-4 text-fg-faint" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* Budget snapshot */}
          <div className="glass rounded-[var(--radius-card)] p-5">
            <h3 className="text-sm font-semibold tracking-tight text-fg">Budget Snapshot</h3>
            <p className="mt-0.5 text-xs text-fg-muted">This month&apos;s runway</p>
            <dl className="mt-4 space-y-2.5 text-sm">
              <div className="flex items-center justify-between">
                <dt className="text-fg-muted">Monthly limit</dt>
                <dd className="data text-fg">{formatCurrency(totalBudget)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-fg-muted">Spent so far</dt>
                <dd className="data text-fg">{formatCurrency(totalExpense)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-fg-muted">Remaining</dt>
                <dd className={`data ${totalBudget - totalExpense >= 0 ? 'text-accent' : 'text-danger'}`}>
                  {formatCurrency(totalBudget - totalExpense)}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-fg-muted">Safe per day</dt>
                <dd className="data text-fg">{formatCurrency(safePerDay)}</dd>
              </div>
            </dl>
            <div className="mt-4">
              <ProgressBar value={budgetUtil} label="Utilization" />
            </div>
          </div>
        </div>
      </section>

      <TransactionLogger open={loggerOpen} onClose={() => setLoggerOpen(false)} onSuccess={loadData} />
    </div>
  )
}
