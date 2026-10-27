export default function FormField({ label, id, error, hint, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-fg-muted">
        {label}
      </label>
      {children}
      {hint && !error ? <p className="text-xs text-fg-faint">{hint}</p> : null}
      {error ? (
        <p className="text-xs font-medium text-danger" id={`${id}-error`} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

export const inputClass =
  'w-full rounded-xl border border-line bg-surface/80 px-4 py-2.5 text-sm text-fg placeholder:text-fg-faint outline-none transition-all duration-200 hover:border-line-strong focus:border-accent focus:bg-surface focus:ring-2 focus:ring-accent/20'
