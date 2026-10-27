const STATUS = {
  safe: { label: 'Safe', text: 'text-accent', stroke: 'stroke-accent' },
  warn: { label: 'Warning', text: 'text-warn', stroke: 'stroke-warn' },
  over: { label: 'Over budget', text: 'text-danger', stroke: 'stroke-danger' },
}

/**
 * Circular budget-utilization gauge.
 * Zones are always accompanied by a text label (a11y: color is not the only indicator).
 */
export default function BudgetGauge({ value = 0, spent = 0, limit = 0 }) {
  const clamped = Math.max(0, Math.min(100, value))
  const status = clamped >= 100 ? STATUS.over : clamped >= 75 ? STATUS.warn : STATUS.safe

  const size = 150
  const stroke = 13
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const arc = 0.75 // 270° arc
  const dash = circumference * arc
  const filled = dash * (clamped / 100)

  return (
    <div className="relative flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-[135deg]" role="img" aria-label={`Budget utilization ${Math.round(clamped)} percent, status ${status.label}`}>
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(148,163,184,0.14)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
        {/* Filled arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className={status.stroke}
          style={{ transition: 'stroke-dasharray 0.9s cubic-bezier(0.22,1,0.36,1)' }}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
        <span className={`data text-3xl font-semibold ${status.text}`}>{Math.round(clamped)}%</span>
        <span className={`mt-1 text-[11px] font-semibold uppercase tracking-wider ${status.text}`}>
          {status.label}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-4 text-xs text-fg-muted" aria-hidden="true">
        <span>Spent <span className="data text-fg">₹{Number(spent).toLocaleString('en-IN')}</span></span>
        <span className="h-3 w-px bg-line" />
        <span>Limit <span className="data text-fg">₹{Number(limit).toLocaleString('en-IN')}</span></span>
      </div>
    </div>
  )
}
