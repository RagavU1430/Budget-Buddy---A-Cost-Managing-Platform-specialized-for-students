import { Download, Lock } from 'lucide-react'
import { useEffect, useState } from 'react'

import { generateReport, getReports, downloadReport } from '../api/reports'
import { useAuth } from '../context/AuthContext'
import { formatCurrency } from '../utils/format'

export default function ReportGenerator() {
  const { user } = useAuth()
  const [form, setForm] = useState({ report_type: 'monthly', month: new Date().toISOString().slice(0, 10), file_format: 'pdf' })
  const [reports, setReports] = useState([])
  const [busy, setBusy] = useState(false)
  const premium = user?.role === 'premium' || user?.role === 'admin'

  const load = async () => {
    try {
      const { data } = await getReports()
      setReports(Array.isArray(data) ? data : data?.results || [])
    } catch { setReports([]) }
  }
  useEffect(() => { if (premium) load() }, [premium])

  if (!premium) return <div className="flex items-center gap-3 rounded-2xl border border-warn/30 bg-warn-soft p-5"><Lock className="h-5 w-5 text-warn" /><div><p className="font-semibold">Premium reports</p><p className="text-sm text-fg-muted">Upgrade to Premium to generate reports.</p></div></div>

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    try { await generateReport(form); await load() } finally { setBusy(false) }
  }
  const download = async (report) => {
    const response = await downloadReport(report.id)
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `budgetbuddy-${report.month}.${report.file_format === 'excel' ? 'xlsx' : 'pdf'}`
    link.click()
    URL.revokeObjectURL(url)
  }

  return <section className="glass rounded-[var(--radius-card)] p-5">
    <div className="mb-4"><p className="label text-accent">Reports</p><h2 className="mt-1 text-lg font-semibold">Generate a financial report</h2></div>
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
      <select value={form.report_type} onChange={(e) => setForm({ ...form, report_type: e.target.value })} className="rounded-xl border border-line bg-white/5 px-3 py-2.5 text-sm text-fg"><option value="monthly">Monthly summary</option><option value="expense">Expense report</option><option value="income">Income report</option><option value="savings">Savings report</option></select>
      <input type="date" value={form.month} onChange={(e) => setForm({ ...form, month: e.target.value })} className="rounded-xl border border-line bg-white/5 px-3 py-2.5 text-sm text-fg" />
      <div className="flex gap-2"><select value={form.file_format} onChange={(e) => setForm({ ...form, file_format: e.target.value })} className="rounded-xl border border-line bg-white/5 px-3 py-2.5 text-sm text-fg"><option value="pdf">PDF</option><option value="excel">Excel</option></select><button disabled={busy} className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-on-accent disabled:opacity-50">{busy ? 'Generating…' : 'Generate'}</button></div>
    </form>
    {reports.length ? <div className="mt-5 divide-y divide-line border-t border-line">{reports.slice(0, 5).map((report) => <div key={report.id} className="flex items-center justify-between gap-3 py-3 text-sm"><span><span className="font-medium">{report.month} · {report.report_type}</span><span className="ml-2 text-xs uppercase text-fg-faint">{report.file_format}</span>{report.summary?.total_expense ? <span className="ml-2 text-xs text-fg-muted">{formatCurrency(report.summary.total_expense)} spent</span> : null}</span><button type="button" onClick={() => download(report)} className="flex items-center gap-1 text-accent hover:underline"><Download className="h-4 w-4" /> Download</button></div>)}</div> : null}
  </section>
}
