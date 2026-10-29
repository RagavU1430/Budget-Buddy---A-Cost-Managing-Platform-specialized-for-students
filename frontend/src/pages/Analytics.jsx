import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'

import { getMonthlySummary, getMonthlyTrends } from '../api/analytics'
import BarChart from '../components/BarChart'
import ProgressBar from '../components/ProgressBar'
import ReportGenerator from '../components/ReportGenerator'
import { SkeletonCard } from '../components/Skeleton'
import { formatCurrency } from '../utils/format'

const monthValue = () => new Date().toISOString().slice(0, 7)
const normalize = (data) => Array.isArray(data) ? data : data?.results || []

export default function Analytics() {
  const [month, setMonth] = useState(monthValue())
  const [summary, setSummary] = useState(null)
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    setLoading(true)
    Promise.all([getMonthlySummary(month), getMonthlyTrends(6)]).then(([summaryResponse, trendResponse]) => { setSummary(summaryResponse.data); setTrends(normalize(trendResponse.data)) }).catch(() => { setSummary(null); setTrends([]) }).finally(() => setLoading(false))
  }, [month])

  const stat = summary || {}
  const cards = [['Total income', formatCurrency(stat.total_income)], ['Total expense', formatCurrency(stat.total_expense)], ['Net balance', formatCurrency(stat.net_balance)], ['Budget utilization', `${Number(stat.budget_utilization_pct || 0).toFixed(0)}%`]]
  return <div className="flex flex-col gap-6"><header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="label text-accent">Analytics</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Financial Analytics 📊</h1><p className="mt-1 text-sm text-fg-muted">See where your money goes and how your habits trend.</p></div><input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-full border border-line bg-white/5 px-4 py-2 text-sm text-fg" /></header>{loading ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[1, 2, 3, 4].map((item) => <SkeletonCard key={item} />)}</div> : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value]) => <article key={label} className="glass rounded-[var(--radius-card)] p-5"><p className="label">{label}</p><p className="data mt-2 text-2xl font-semibold">{value}</p></article>)}</div>}<div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]"><section className="glass rounded-[var(--radius-card)] p-5"><div className="mb-4"><p className="label text-accent">Trends</p><h2 className="mt-1 text-lg font-semibold">Last six months</h2></div><BarChart data={trends} /></section><section className="glass rounded-[var(--radius-card)] p-5"><p className="label text-accent">Category breakdown</p><h2 className="mt-1 text-lg font-semibold">{stat.month || month}</h2><div className="mt-5 space-y-4">{(stat.category_breakdown || []).length ? stat.category_breakdown.map((item) => <div key={item.category}><div className="mb-1 flex justify-between text-sm"><span className="capitalize text-fg-muted">{item.category.replaceAll('_', ' ')}</span><span className="data">{formatCurrency(item.spent)}</span></div><ProgressBar value={item.utilization_pct} /></div>) : <p className="py-8 text-sm text-fg-muted">No category spending recorded.</p>}</div></section></div><div className="grid gap-6 lg:grid-cols-3"><section className="glass rounded-[var(--radius-card)] p-5"><p className="label text-accent">Payment methods</p><div className="mt-4 space-y-3">{(stat.payment_method_breakdown || []).map((item) => <div key={item.method} className="flex justify-between text-sm"><span className="capitalize text-fg-muted">{item.method}</span><span className="data">{formatCurrency(item.total)}</span></div>)}</div></section><section className="glass rounded-[var(--radius-card)] p-5"><p className="label text-accent">Top expense</p>{stat.top_expense ? <><p className="mt-3 font-semibold">{stat.top_expense.title}</p><p className="data mt-1 text-2xl text-danger">{formatCurrency(stat.top_expense.amount)}</p><p className="mt-1 text-xs text-fg-muted">{stat.top_expense.category} · {stat.top_expense.date}</p></> : <p className="mt-4 text-sm text-fg-muted">No expenses recorded.</p>}</section><section className="glass rounded-[var(--radius-card)] p-5"><p className="label text-accent">Safe daily spend</p><p className="data mt-3 text-2xl font-semibold text-accent">{formatCurrency(stat.safe_daily_spend)}</p><p className="mt-1 text-xs text-fg-muted">{stat.remaining_days || 0} days remaining</p>{Number(stat.budget_utilization_pct) >= 100 ? <p className="mt-4 flex gap-2 text-xs text-danger"><AlertTriangle className="h-4 w-4" /> Budget exceeded</p> : null}</section></div><ReportGenerator /></div>
}
