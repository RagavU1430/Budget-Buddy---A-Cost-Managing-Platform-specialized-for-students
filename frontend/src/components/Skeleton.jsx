export function SkeletonLine({ className = '' }) {
  return <div className={`skeleton h-3 ${className}`} aria-hidden="true" />
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`glass rounded-[var(--radius-card)] p-5 ${className}`} aria-hidden="true">
      <SkeletonLine className="w-24" />
      <SkeletonLine className="mt-3 h-7 w-32" />
      <SkeletonLine className="mt-3 w-20" />
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 px-6 py-4" aria-hidden="true">
      <div className="skeleton h-9 w-9 shrink-0 rounded-full" />
      <div className="flex-1">
        <SkeletonLine className="w-40" />
        <SkeletonLine className="mt-2 w-24 opacity-70" />
      </div>
      <SkeletonLine className="h-4 w-20" />
    </div>
  )
}

export function SkeletonList({ count = 5, label = 'Loading' }) {
  return (
    <div role="status" aria-busy="true" aria-label={label}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  )
}
