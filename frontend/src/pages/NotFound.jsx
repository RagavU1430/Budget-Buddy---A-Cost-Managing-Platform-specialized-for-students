import { ArrowLeft, Compass, Home, RotateCcw } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

export default function NotFound() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4 text-center">
      {/* Background ambient glow */}
      <div
        className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-accent/20 blur-[120px]"
        aria-hidden="true"
      />

      <div className="glass-strong relative w-full max-w-lg rounded-3xl border border-line-strong p-8 shadow-2xl sm:p-10">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-soft text-accent ring-1 ring-accent/30 shadow-glow">
          <Compass className="h-8 w-8 animate-pulse" />
        </div>

        <p className="mt-6 text-6xl font-extrabold tracking-tight text-fg font-['Outfit']">404</p>
        <h1 className="mt-2 text-xl font-bold text-fg font-['Outfit']">Page not found</h1>
        <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-fg-muted">
          We could not find the page you requested. It may have been moved, deleted, or the address may be incorrect.
        </p>

        <p className="mt-4 truncate rounded-lg border border-line bg-white/5 px-3 py-2 font-mono text-xs text-fg-faint" title={location.pathname}>
          {location.pathname}
        </p>

        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            to="/"
            className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-bold text-on-accent transition-all duration-200 hover:bg-accent-hover hover:shadow-glow"
          >
            <Home className="h-4 w-4" />
            <span>Go to Dashboard</span>
          </Link>
          <button
            type="button"
            onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
            className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-line bg-white/5 px-5 py-2.5 text-sm font-semibold text-fg transition-colors hover:bg-white/10"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Go back</span>
          </button>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-line bg-white/5 px-5 py-2.5 text-sm font-semibold text-fg-muted transition-colors hover:bg-white/10 hover:text-fg"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    </main>
  )
}
