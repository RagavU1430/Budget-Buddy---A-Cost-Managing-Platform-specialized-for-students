import { formatCurrency } from '../utils/format'

export default function BarChart({ data = [], height = 220 }) {
  const width = 720
  const pad = { top: 16, right: 12, bottom: 34, left: 58 }
  const chartHeight = height - pad.top - pad.bottom
  const max = Math.max(1, ...data.flatMap((item) => [Number(item.income) || 0, Number(item.expense) || 0, Number(item.budget) || 0]))
  const groupWidth = data.length ? (width - pad.left - pad.right) / data.length : 0
  const barWidth = Math.max(5, Math.min(18, groupWidth / 5))
  const y = (value) => pad.top + chartHeight - (Number(value || 0) / max) * chartHeight

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="min-w-[560px] w-full" role="img" aria-label="Monthly income, expense and budget chart">
        {[0, 0.5, 1].map((step) => (
          <g key={step}>
            <line x1={pad.left} x2={width - pad.right} y1={pad.top + chartHeight * step} y2={pad.top + chartHeight * step} stroke="rgba(148,163,184,.14)" />
            <text x={pad.left - 8} y={pad.top + chartHeight * step + 4} textAnchor="end" fill="var(--color-fg-faint)" fontSize="10">
              {formatCurrency(max * (1 - step)).replace('.00', '')}
            </text>
          </g>
        ))}
        {data.map((item, index) => {
          const center = pad.left + groupWidth * index + groupWidth / 2
          const values = [
            { key: 'income', value: item.income, fill: 'var(--color-accent)' },
            { key: 'expense', value: item.expense, fill: 'var(--color-danger)' },
            { key: 'budget', value: item.budget, fill: 'var(--color-warn)' },
          ]
          return (
            <g key={item.month || item.month_label || index}>
              {values.map((bar, barIndex) => {
                const value = Number(bar.value) || 0
                const barHeight = (value / max) * chartHeight
                return <rect key={bar.key} x={center + (barIndex - 1) * (barWidth + 3) - barWidth / 2} y={y(value)} width={barWidth} height={barHeight} rx="3" fill={bar.fill} opacity=".9" />
              })}
              <text x={center} y={height - 10} textAnchor="middle" fill="var(--color-fg-faint)" fontSize="10">{item.month_label || item.label}</text>
            </g>
          )
        })}
      </svg>
      <div className="mt-2 flex justify-center gap-4 text-xs text-fg-muted">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-accent" />Income</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-danger" />Expense</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-warn" />Budget</span>
      </div>
    </div>
  )
}
