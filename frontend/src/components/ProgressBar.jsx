export default function ProgressBar({ value = 0, label }) {
  const clamped = Math.max(0, Math.min(120, value))
  const width = Math.min(100, clamped)

  let bar = 'bg-accent'
  let text = 'text-accent'
  if (clamped >= 75 && clamped < 100) {
    bar = 'bg-warn'
    text = 'text-warn'
  }
  if (clamped >= 100) {
    bar = 'bg-danger'
    text = 'text-danger'
  }

  return (
    <div>
      {label ? (
        <div className="mb-1.5 flex items-center justify-between text-xs">
          <span className="text-fg-muted">{label}</span>
          <span className={`data font-semibold ${text}`}>{clamped.toFixed(0)}%</span>
        </div>
      ) : null}
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-white/6"
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? 'Progress'}
      >
        <div
          className={`h-full rounded-full transition-[width] duration-700 ease-out ${bar}`}
          style={{ width: `${width}%`, boxShadow: clamped >= 100 ? '0 0 12px rgba(239,68,68,0.6)' : undefined }}
        />
      </div>
    </div>
  )
}
