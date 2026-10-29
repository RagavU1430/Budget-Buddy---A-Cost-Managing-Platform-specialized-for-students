import { ArrowUpRight, CheckCircle2, AlertTriangle, ShieldCheck, Target } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatCurrency } from '../utils/format'

const STATUS = {
  none: {
    id: 'none',
    label: 'No Limit Set',
    text: 'text-fg-muted',
    bg: 'bg-white/5 ring-line text-fg-muted',
    gradient: ['#64748B', '#94A3B8'],
    dot: 'bg-fg-muted',
  },
  safe: {
    id: 'safe',
    label: 'On Track',
    text: 'text-accent',
    bg: 'bg-accent-soft ring-accent/30 text-accent',
    gradient: ['#10B981', '#34D399'],
    dot: 'bg-accent shadow-[0_0_8px_var(--color-accent)]',
  },
  warn: {
    id: 'warn',
    label: '80% Warning',
    text: 'text-warn',
    bg: 'bg-warn-soft ring-warn/30 text-warn',
    gradient: ['#F59E0B', '#FBBF24'],
    dot: 'bg-warn shadow-[0_0_8px_var(--color-warn)]',
  },
  over: {
    id: 'over',
    label: 'Over Budget',
    text: 'text-danger',
    bg: 'bg-danger-soft ring-danger/30 text-danger',
    gradient: ['#F43F5E', '#FB7185'],
    dot: 'bg-danger shadow-[0_0_8px_var(--color-danger)] animate-ping',
  },
}

export default function BudgetGauge({ value = 0, spent = 0, limit = 0 }) {
  const hasLimit = Number(limit) > 0
  const clamped = Math.max(0, Math.min(100, Number(value || 0)))

  const status = !hasLimit
    ? STATUS.none
    : clamped >= 100
      ? STATUS.over
      : clamped >= 80
        ? STATUS.warn
        : STATUS.safe

  const size = 144
  const stroke = 11
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const arc = 0.75 // 270 degree gauge
  const dash = circumference * arc
  const filled = dash * (clamped / 100)
  const remaining = Number(limit) - Number(spent)

  return (
    <div className="relative flex flex-col items-center">
      {/* SVG Radial Gauge */}
      <div className="relative flex items-center justify-center">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="-rotate-[135deg]"
          role="img"
          aria-label={`Budget utilization ${Math.round(clamped)} percent`}
        >
          <defs>
            {/* Gradients */}
            <linearGradient id="gauge-gradient-safe" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#059669" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
            <linearGradient id="gauge-gradient-warn" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#D97706" />
              <stop offset="100%" stopColor="#FBBF24" />
            </linearGradient>
            <linearGradient id="gauge-gradient-over" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#E11D48" />
              <stop offset="100%" stopColor="#FB7185" />
            </linearGradient>
            <linearGradient id="gauge-gradient-none" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#475569" />
              <stop offset="100%" stopColor="#64748B" />
            </linearGradient>

            {/* Subtle glow filter */}
            <filter id="gauge-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(148, 163, 184, 0.12)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
          />

          {/* Filled Arc — Only rendered when clamped > 0 to prevent floating stray dot bug */}
          {clamped > 0 && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={`url(#gauge-gradient-${status.id})`}
              filter="url(#gauge-glow)"
              style={{
                transition: 'stroke-dasharray 0.9s cubic-bezier(0.22, 1, 0.36, 1)',
              }}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${filled} ${circumference}`}
            />
          )}
        </svg>

        {/* Center Typography & Badge */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pt-2 select-none">
          <div className="flex items-baseline">
            <span className={`data text-3xl font-bold font-['Outfit'] tracking-tight ${status.text}`}>
              {hasLimit ? Math.round(clamped) : 0}
            </span>
            <span className={`text-base font-semibold ml-0.5 ${status.text}`}>%</span>
          </div>

          <span
            className={`mt-1 flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${status.bg}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </span>
        </div>
      </div>

      {/* Bottom Metrics Pill Bar */}
      <div className="mt-3.5 w-full">
        <div className="grid grid-cols-2 gap-2 rounded-2xl border border-line/60 bg-white/[0.02] p-2 text-xs">
          <div className="flex flex-col items-center border-r border-line/60 px-1">
            <span className="text-[10px] uppercase font-semibold tracking-wider text-fg-faint">Spent</span>
            <span className="data mt-0.5 font-semibold text-fg">
              {formatCurrency(Number(spent || 0))}
            </span>
          </div>

          <div className="flex flex-col items-center px-1">
            <span className="text-[10px] uppercase font-semibold tracking-wider text-fg-faint">Limit</span>
            <span className="data mt-0.5 font-semibold text-fg">
              {hasLimit ? formatCurrency(Number(limit)) : 'None'}
            </span>
          </div>
        </div>

        {/* Runway status or Call to action */}
        <div className="mt-2 text-center">
          {hasLimit ? (
            <p className="text-[11px] text-fg-muted">
              {remaining >= 0 ? (
                <span>
                  <strong className="text-accent">{formatCurrency(remaining)}</strong> remaining runway
                </span>
              ) : (
                <span className="text-danger font-medium">
                  Exceeded by {formatCurrency(Math.abs(remaining))}
                </span>
              )}
            </p>
          ) : (
            <Link
              to="/budgets"
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-accent hover:underline"
            >
              <span>Set category limits</span>
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
