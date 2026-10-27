import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

export default function Modal({ open, onClose, title, subtitle, children }) {
  const panelRef = useRef(null)
  const lastActiveRef = useRef(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!open) return undefined

    lastActiveRef.current = document.activeElement
    const panel = panelRef.current

    // Set initial focus only if focus is not already inside the modal panel
    if (panel && !panel.contains(document.activeElement)) {
      const firstInput = panel.querySelector(
        'input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
      )
      const target = firstInput || panel.querySelector(FOCUSABLE)
      target?.focus()
    }

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onCloseRef.current?.()
        return
      }
      if (e.key !== 'Tab' || !panel) return

      // Focus trap — keep Tab cycling inside the modal
      const nodes = [...panel.querySelectorAll(FOCUSABLE)].filter((n) => n.offsetParent !== null)
      if (nodes.length === 0) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.style.overflow = prevOverflow
      lastActiveRef.current?.focus?.()
    }
  }, [open])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-[rgba(2,6,23,0.75)] p-0 backdrop-blur-sm sm:items-center sm:p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose?.()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="glass-strong max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-t-3xl p-6 animate-[rise_0.35s_cubic-bezier(0.22,1,0.36,1)_both] sm:rounded-3xl"
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-fg">{title}</h2>
            {subtitle ? <p className="mt-0.5 text-sm text-fg-muted">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="cursor-pointer rounded-full border border-line bg-white/5 p-1.5 text-fg-muted transition-colors duration-200 hover:bg-white/10 hover:text-fg"
          >
            <X className="h-4.5 w-4.5" aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
