export default function Alert({ message, type = 'error' }) {
  if (!message) return null

  const styles =
    type === 'error'
      ? 'bg-red-50 text-red-700 border-red-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200'

  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${styles}`} role="alert">
      {message}
    </div>
  )
}
