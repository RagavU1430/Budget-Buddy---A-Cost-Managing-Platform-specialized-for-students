import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Plus, Trash2 } from 'lucide-react'

import { createGoal, deleteGoal, depositToGoal, getGoals } from '../api/goals'
import GoalProgressRing from '../components/GoalProgressRing'
import Modal from '../components/Modal'
import FormField, { inputClass } from '../components/FormField'
import { SkeletonCard } from '../components/Skeleton'
import { formatCurrency } from '../utils/format'

const emptyGoal = { title: '', description: '', target_amount: '', target_date: '', priority: 'medium' }
const normalize = (data) => Array.isArray(data) ? data : data?.results || []
const priorityClass = { low: 'bg-info-soft text-info', medium: 'bg-warn-soft text-warn', high: 'bg-danger-soft text-danger' }

export default function Goals() {
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyGoal)
  const [amount, setAmount] = useState('')

  const load = async () => {
    try { const { data } = await getGoals(); setGoals(normalize(data)) } catch { setGoals([]) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  const visible = useMemo(() => goals.filter((goal) => filter === 'all' || (filter === 'completed' ? goal.is_completed : !goal.is_completed)), [goals, filter])
  const summary = { total: goals.length, active: goals.filter((g) => !g.is_completed).length, completed: goals.filter((g) => g.is_completed).length, saved: goals.reduce((sum, g) => sum + Number(g.current_amount || 0), 0) }

  const save = async (event) => {
    event.preventDefault()
    await createGoal({ ...form, target_amount: Number(form.target_amount), target_date: form.target_date || null })
    setModal(null); setForm(emptyGoal); await load()
  }
  const deposit = async (event) => {
    event.preventDefault()
    await depositToGoal(modal.id, Number(amount)); setModal(null); setAmount(''); await load()
  }
  const remove = async (id) => { if (window.confirm('Delete this goal?')) { await deleteGoal(id); await load() } }

  return <div className="flex flex-col gap-6">
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="label text-accent">Goals</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Savings Goals</h1><p className="mt-1 text-sm text-fg-muted">Turn your plans into progress, one deposit at a time.</p></div><button type="button" onClick={() => setModal('new')} className="flex items-center gap-2 self-start rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-on-accent"><Plus className="h-4 w-4" /> New Goal</button></header>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[['Total goals', summary.total], ['Active goals', summary.active], ['Completed goals', summary.completed], ['Total saved', formatCurrency(summary.saved)]].map(([label, value]) => <article key={label} className="glass rounded-[var(--radius-card)] p-5"><p className="label">{label}</p><p className="data mt-2 text-2xl font-semibold text-fg">{value}</p></article>)}</section>
    <div className="flex gap-2 border-b border-line">{['all', 'active', 'completed'].map((tab) => <button type="button" key={tab} onClick={() => setFilter(tab)} className={`border-b-2 px-3 py-2 text-sm font-medium capitalize ${filter === tab ? 'border-accent text-accent' : 'border-transparent text-fg-muted'}`}>{tab}</button>)}</div>
    <section className="grid gap-4 md:grid-cols-2" aria-label="Savings goals">{loading ? [1, 2, 3, 4].map((item) => <SkeletonCard key={item} />) : visible.length === 0 ? <div className="glass col-span-full rounded-[var(--radius-card)] p-12 text-center"><CheckCircle2 className="mx-auto h-8 w-8 text-fg-faint" /><p className="mt-3 font-semibold">No goals here yet</p><p className="mt-1 text-sm text-fg-muted">Create a goal and start building your future.</p></div> : visible.map((goal) => { const progress = Number(goal.progress_pct ?? (Number(goal.current_amount || 0) / Number(goal.target_amount || 1)) * 100); return <article key={goal.id} className="glass rounded-[var(--radius-card)] p-5"><div className="flex items-start justify-between gap-4"><div className="min-w-0"><div className="flex items-center gap-2"><h2 className="truncate text-lg font-semibold">{goal.title}</h2><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${priorityClass[goal.priority] || priorityClass.medium}`}>{goal.priority}</span></div><p className="mt-1 line-clamp-2 text-sm text-fg-muted">{goal.description || 'No description'}</p></div><GoalProgressRing value={progress} color={progress >= 100 ? 'accent' : 'amber'} /></div><div className="mt-5 flex items-end justify-between"><div><p className="label">Saved</p><p className="data mt-1 text-xl font-semibold">{formatCurrency(goal.current_amount)} <span className="text-sm font-normal text-fg-muted">/ {formatCurrency(goal.target_amount)}</span></p></div><p className="text-xs text-fg-faint">{goal.target_date ? `Due ${goal.target_date}` : 'No deadline'}</p></div><div className="mt-5 flex gap-2"><button type="button" onClick={() => setModal(goal)} disabled={goal.is_completed} className="flex-1 rounded-full bg-accent px-3 py-2 text-sm font-semibold text-on-accent disabled:opacity-50">Deposit</button><button type="button" onClick={() => remove(goal.id)} aria-label={`Delete ${goal.title}`} className="rounded-full border border-line px-3 py-2 text-danger hover:bg-danger-soft"><Trash2 className="h-4 w-4" /></button></div></article> })}</section>
    <Modal open={modal === 'new'} onClose={() => setModal(null)} title="Create savings goal" subtitle="Choose a target that motivates you"><form onSubmit={save} className="flex flex-col gap-4"><FormField label="Title" id="goal-title"><input id="goal-title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inputClass} placeholder="Emergency fund" /></FormField><FormField label="Description" id="goal-description"><textarea id="goal-description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={`${inputClass} min-h-20`} /></FormField><div className="grid gap-3 sm:grid-cols-2"><FormField label="Target amount" id="goal-amount"><input id="goal-amount" required type="number" min="1" step="0.01" value={form.target_amount} onChange={(e) => setForm({ ...form, target_amount: e.target.value })} className={inputClass} /></FormField><FormField label="Target date" id="goal-date"><input id="goal-date" type="date" value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} className={inputClass} /></FormField></div><FormField label="Priority" id="goal-priority"><select id="goal-priority" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} className={inputClass}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></FormField><button className="rounded-full bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent">Create goal</button></form></Modal>
    <Modal open={modal && modal !== 'new'} onClose={() => setModal(null)} title={`Deposit into ${modal?.title || ''}`}><form onSubmit={deposit} className="flex flex-col gap-4"><FormField label="Amount" id="deposit-amount"><input id="deposit-amount" required type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClass} placeholder="1000" /></FormField><button className="rounded-full bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent">Add deposit</button></form></Modal>
  </div>
}
