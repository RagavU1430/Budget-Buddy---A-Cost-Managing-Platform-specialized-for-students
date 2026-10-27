const tones = {
  neutral: { card: 'border-line', icon: 'bg-white/5 text-fg-muted ring-line' },
  green: { card: 'border-accent/25', icon: 'bg-accent-soft text-accent ring-accent/30' },
  rose: { card: 'border-danger/25', icon: 'bg-danger-soft text-danger ring-danger/30' },
  amber: { card: 'border-warn/25', icon: 'bg-warn-soft text-warn ring-warn/30' },
  sky: { card: 'border-info/25', icon: 'bg-info-soft text-info ring-info/30' },
}

export default function StatCard({ title, value, icon: Icon, trend, tone = 'neutral', delay = 0 }) {
  const t = tones[tone] ?? tones.neutral

  return (
    <article
      className={`glass relative overflow-hidden rounded-[var(--radius-card)] p-5 transition-transform duration-200 hover:-translate-y-0.5 ${t.card} animate-[rise_0.5s_cubic-bezier(0.22,1,0.36,1)_both]`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="label">{title}</p>
          <p className="data mt-2.5 truncate text-[1.75rem] leading-none font-semibold text-fg" title={String(value)}>
            {value}
          </p>
          {trend ? (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-fg-muted">
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${tone === 'rose' ? 'bg-danger' : 'bg-accent'}`} aria-hidden="true" />
              {trend}
            </p>
          ) : null}
        </div>
        {Icon ? (
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ${t.icon}`} aria-hidden="true">
            <Icon className="h-5 w-5" />
          </span>
        ) : null}
      </div>
    </article>
  )
}
