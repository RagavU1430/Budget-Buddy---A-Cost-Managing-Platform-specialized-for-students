import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 text-center">
      <p className="text-5xl font-bold text-slate-900">404</p>
      <p className="text-slate-500">This page does not exist.</p>
      <Link
        to="/"
        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
      >
        Back to dashboard
      </Link>
    </div>
  )
}
