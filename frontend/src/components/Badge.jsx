const tones = {
  neutral: 'bg-white/6 text-fg-muted ring-line',
  green: 'bg-accent-soft text-accent ring-accent/30',
  rose: 'bg-danger-soft text-danger ring-danger/30',
  amber: 'bg-warn-soft text-warn ring-warn/30',
  violet: 'bg-[rgba(139,92,246,0.14)] text-violet-300 ring-violet-400/30',
  sky: 'bg-info-soft text-info ring-info/30',
}

export default function Badge({ children, tone = 'neutral', dot = false }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ring-1 ${
        tones[tone] ?? tones.neutral
      }`}
    >
      {dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}
