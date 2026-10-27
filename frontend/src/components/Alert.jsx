import { AlertCircle, CheckCircle2 } from 'lucide-react'

export default function Alert({ message, type = 'error' }) {
  if (!message) return null

  const isError = type === 'error'
  const Icon = isError ? AlertCircle : CheckCircle2
  const styles = isError
    ? 'border-danger/30 bg-danger-soft text-danger'
    : 'border-accent/30 bg-accent-soft text-accent'

  return (
    <div className={`flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm ${styles}`} role="alert">
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  )
}
