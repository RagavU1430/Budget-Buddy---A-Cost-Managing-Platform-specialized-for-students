import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'

export default function DropdownSelect({
  value,
  onChange,
  options = [],
  icon: Icon,
  iconClass = 'text-accent',
  ariaLabel,
  className = '',
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open])

  const selectedOption = options.find((opt) => opt.value === value) || options[0]

  return (
    <div ref={ref} className={`relative inline-block ${className}`}>
      {/* Clickable pill trigger */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel || selectedOption?.label}
        className={`flex items-center gap-2 rounded-full border px-3.5 py-2 text-sm font-medium transition-all duration-200 cursor-pointer select-none ${
          open
            ? 'border-accent bg-accent/15 text-fg shadow-glow ring-1 ring-accent/40'
            : 'border-line bg-white/4 text-fg-muted hover:border-line-strong hover:bg-white/8 hover:text-fg'
        }`}
      >
        {Icon && <Icon className={`h-4 w-4 shrink-0 ${iconClass}`} aria-hidden="true" />}
        <span className="text-fg text-sm">{selectedOption?.label}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 text-fg-faint transition-transform duration-200 ${
            open ? 'rotate-180 text-accent' : ''
          }`}
          aria-hidden="true"
        />
      </button>

      {/* Floating Menu */}
      {open && (
        <div
          role="listbox"
          className="absolute left-0 top-full mt-2 z-50 min-w-[190px] max-h-64 overflow-y-auto rounded-2xl border border-line-strong bg-surface-2/95 p-1.5 shadow-2xl backdrop-blur-2xl animate-[rise_0.2s_cubic-bezier(0.22,1,0.36,1)_both] scrollbar-thin"
        >
          {options.map((opt) => {
            const isSelected = opt.value === value
            return (
              <button
                key={opt.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(opt.value)
                  setOpen(false)
                }}
                className={`flex w-full items-center justify-between gap-2.5 rounded-xl px-3 py-2 text-xs font-medium text-left transition-colors duration-150 cursor-pointer ${
                  isSelected
                    ? 'bg-accent/15 text-accent font-semibold'
                    : 'text-fg-muted hover:bg-white/5 hover:text-fg'
                }`}
              >
                <span className="truncate">{opt.label}</span>
                {isSelected && <Check className="h-3.5 w-3.5 shrink-0 text-accent" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
