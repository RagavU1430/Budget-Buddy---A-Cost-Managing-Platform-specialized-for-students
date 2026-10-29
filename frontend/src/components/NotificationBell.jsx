import { Bell, Check, Info, Target, Wallet, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { getNotifications, getUnreadCount, markAllRead, markNotificationRead } from '../api/notifications'

const icons = { budget: Wallet, goal: Target, savings: Wallet, system: Info, report: Info }
const relativeTime = (date) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 1000))
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(false)
  const ref = useRef(null)

  const load = async () => {
    setLoading(true)
    try {
      const [list, count] = await Promise.all([getNotifications({ page_size: 10 }), getUnreadCount()])
      const items = Array.isArray(list.data) ? list.data : list.data?.results || []
      setNotifications(items.slice(0, 10))
      setUnread(Number(count.data?.count ?? count.data?.unread_count ?? 0))
    } catch {
      setNotifications([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    const close = (event) => { if (ref.current && !ref.current.contains(event.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const openPanel = () => { setOpen((value) => !value); if (!open) load() }
  const read = async (item) => {
    if (item.is_read) return
    try { await markNotificationRead(item.id) } catch { return }
    setNotifications((items) => items.map((entry) => entry.id === item.id ? { ...entry, is_read: true } : entry))
    setUnread((value) => Math.max(0, value - 1))
  }
  const readAll = async () => {
    try { await markAllRead(); setNotifications((items) => items.map((item) => ({ ...item, is_read: true }))); setUnread(0) } catch { /* keep current state */ }
  }

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={openPanel} aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} className="relative cursor-pointer rounded-full border border-line bg-white/5 p-2 text-fg-muted hover:bg-white/10 hover:text-fg">
        <Bell className="h-4.5 w-4.5" aria-hidden="true" />
        {unread > 0 ? <span className="absolute -right-1 -top-1 flex min-h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">{unread > 99 ? '99+' : unread}</span> : null}
      </button>
      {open ? (
        <div className="absolute right-0 top-12 z-50 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <p className="text-sm font-semibold">Notifications</p>
            <div className="flex items-center gap-2">
              <button type="button" onClick={readAll} className="text-xs font-medium text-accent hover:underline">Mark all read</button>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close notifications" className="text-fg-muted hover:text-fg"><X className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {loading ? <p className="px-4 py-6 text-center text-sm text-fg-muted">Loading notifications…</p> : notifications.length === 0 ? <p className="px-4 py-6 text-center text-sm text-fg-muted">You’re all caught up.</p> : notifications.map((item) => {
              const Icon = icons[item.notification_type] || Info
              return <button type="button" key={item.id} onClick={() => read(item)} className={`flex w-full gap-3 border-b border-line px-4 py-3 text-left hover:bg-white/5 ${item.is_read ? 'opacity-65' : ''}`}>
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                <span className="min-w-0"><span className="block text-sm font-semibold">{item.title}</span><span className="mt-0.5 block text-xs text-fg-muted">{item.message}</span><span className="mt-1 block text-[11px] text-fg-faint">{relativeTime(item.created_at)}</span></span>
                {!item.is_read ? <Check className="ml-auto mt-1 h-3.5 w-3.5 shrink-0 text-accent" /> : null}
              </button>
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
}
