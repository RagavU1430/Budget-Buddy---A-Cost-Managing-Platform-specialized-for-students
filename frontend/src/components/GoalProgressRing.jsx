export default function GoalProgressRing({ value = 0, size = 80, strokeWidth = 8, color = 'accent' }) {
  const progress = Math.min(100, Math.max(0, Number(value) || 0))
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const colorMap = { accent: 'var(--color-accent)', danger: 'var(--color-danger)', amber: 'var(--color-warn)' }
  const stroke = colorMap[color] || colorMap.accent

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${progress.toFixed(0)}% complete`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(148,163,184,.16)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress / 100)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <span className="data absolute inset-0 flex items-center justify-center text-xs font-semibold text-fg">{progress.toFixed(0)}%</span>
    </div>
  )
}
