import { ArrowLeft, Compass, Wallet } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 text-center">
      {/* Background ambient glow */}
      <div
        className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-accent/20 blur-[120px]"
        aria-hidden="true"
      />

      <div className="glass-strong relative max-w-md rounded-3xl p-8 sm:p-10 border border-line-strong shadow-2xl">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-soft text-accent ring-1 ring-accent/30 shadow-glow">
          <Compass className="h-8 w-8 animate-pulse" />
        </div>

        <p className="mt-6 text-6xl font-extrabold tracking-tight text-fg font-['Outfit']">404</p>
        <h1 className="mt-2 text-xl font-bold text-fg font-['Outfit']">Page Not Found</h1>
        <p className="mt-2 text-sm text-fg-muted">
          The requested page could not be located or may have been relocated.
        </p>

        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-bold text-on-accent transition-all duration-200 hover:bg-accent-hover hover:shadow-glow"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
