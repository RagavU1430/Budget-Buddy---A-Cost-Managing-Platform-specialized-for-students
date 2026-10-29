import {
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  FileText,
  Info,
  Sparkles,
  Target,
  Wallet,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import {
  getNotifications,
  getUnreadCount,
  markAllRead,
  markNotificationRead,
} from '../api/notifications'

const typeConfig = {
  budget: {
    icon: AlertTriangle,
    bg: 'bg-danger/15 text-danger ring-danger/30',
    label: 'Budget Alert',
  },
  goal: {
    icon: Target,
    bg: 'bg-accent/15 text-accent ring-accent/30',
    label: 'Goal Milestone',
  },
  savings: {
    icon: Wallet,
    bg: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30',
    label: 'Savings',
  },
  report: {
    icon: FileText,
    bg: 'bg-purple-500/15 text-purple-400 ring-purple-500/30',
    label: 'Monthly Report',
  },
  system: {
    icon: Info,
    bg: 'bg-blue-500/15 text-blue-400 ring-blue-500/30',
    label: 'System Update',
  },
}

const relativeTime = (date) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 1000))
  if (seconds < 60) return 'Just now'
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
      const [list, count] = await Promise.all([
        getNotifications({ page_size: 15 }),
        getUnreadCount(),
      ])
      const items = Array.isArray(list.data) ? list.data : list.data?.results || []
      setNotifications(items.slice(0, 15))
      setUnread(Number(count.data?.count ?? count.data?.unread_count ?? 0))
    } catch {
      setNotifications([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const handleRefresh = () => {
      load()
    }
    window.addEventListener('budgetbuddy:data-refresh', handleRefresh)
    return () => window.removeEventListener('budgetbuddy:data-refresh', handleRefresh)
  }, [])

  useEffect(() => {
    const close = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const openPanel = () => {
    setOpen((value) => !value)
    if (!open) load()
  }

  const read = async (item) => {
    if (item.is_read) return
    try {
      await markNotificationRead(item.id)
    } catch {
      return
    }
    setNotifications((items) =>
      items.map((entry) => (entry.id === item.id ? { ...entry, is_read: true } : entry))
    )
    setUnread((value) => Math.max(0, value - 1))
  }

  const readAll = async () => {
    try {
      await markAllRead()
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })))
      setUnread(0)
    } catch {
      // keep current state
    }
  }

  return (
    <div ref={ref} className="relative">
      {/* Bell Trigger Button */}
      <button
        type="button"
        onClick={openPanel}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
        aria-expanded={open}
        className={`relative flex h-9 w-9 items-center justify-center rounded-full border transition-all duration-200 cursor-pointer ${
          open
            ? 'border-accent/60 bg-accent/15 text-accent shadow-glow'
            : 'border-line bg-white/5 text-fg-muted hover:border-accent/40 hover:bg-white/10 hover:text-fg'
        }`}
      >
        <Bell className="h-4 w-4 transition-transform group-hover:scale-110" aria-hidden="true" />
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white shadow-sm animate-pulse">
            {unread > 99 ? '99+' : unread}
          </span>
        ) : null}
      </button>

      {/* Styled Dropdown Menu */}
      {open ? (
        <div className="absolute right-0 top-12 z-50 w-[min(24rem,calc(100vw-1.5rem))] sm:w-[390px] overflow-hidden rounded-3xl border border-line-strong bg-surface-2/95 shadow-2xl backdrop-blur-2xl animate-[rise_0.25s_cubic-bezier(0.22,1,0.36,1)_both]">
          {/* Ambient glow accent top */}
          <div className="pointer-events-none absolute -top-10 right-10 h-32 w-32 rounded-full bg-accent/15 blur-2xl" />

          {/* Header */}
          <div className="relative flex items-center justify-between border-b border-line/80 bg-surface/80 px-4 py-3.5 backdrop-blur-md">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-accent-soft text-accent ring-1 ring-accent/30 shadow-sm">
                <Sparkles className="h-3.5 w-3.5" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-fg font-['Outfit']">Notifications</h3>
                <p className="text-[11px] text-fg-muted">
                  {unread > 0 ? `${unread} unread update${unread === 1 ? '' : 's'}` : 'All caught up'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              {unread > 0 && (
                <button
                  type="button"
                  onClick={readAll}
                  className="flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft/30 px-2.5 py-1 text-[11px] font-semibold text-accent transition-colors hover:bg-accent-soft hover:text-accent cursor-pointer"
                  title="Mark all notifications as read"
                >
                  <CheckCheck className="h-3 w-3" />
                  <span>Mark all read</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close notifications"
                className="rounded-full p-1.5 text-fg-faint hover:bg-white/5 hover:text-fg transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Notifications List */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-line/40 scrollbar-thin">
            {loading ? (
              <div className="px-4 py-10 text-center">
                <div className="mx-auto h-6 w-6 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                <p className="mt-3 text-xs text-fg-muted">Fetching updates…</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="px-6 py-12 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 ring-1 ring-line text-fg-faint">
                  <Bell className="h-6 w-6" />
                </div>
                <p className="mt-3 text-sm font-semibold text-fg">No notifications yet</p>
                <p className="mt-1 text-xs text-fg-muted max-w-xs mx-auto">
                  You'll see budget alerts, goal milestones, and monthly report updates right here.
                </p>
              </div>
            ) : (
              notifications.map((item) => {
                const config = typeConfig[item.notification_type] || typeConfig.system
                const Icon = config.icon

                return (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => read(item)}
                    className={`relative flex w-full items-start gap-3 px-4 py-3.5 text-left transition-colors duration-150 hover:bg-white/[0.04] cursor-pointer group ${
                      !item.is_read ? 'bg-accent/[0.03]' : 'opacity-70'
                    }`}
                  >
                    {/* Status dot indicator */}
                    {!item.is_read && (
                      <span className="absolute left-1.5 top-4.5 h-1.5 w-1.5 rounded-full bg-accent shadow-[0_0_8px_var(--color-accent)]" />
                    )}

                    {/* Icon container */}
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl ring-1 shadow-sm transition-transform group-hover:scale-105 ${config.bg}`}
                    >
                      <Icon className="h-4.5 w-4.5" />
                    </span>

                    {/* Content */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-xs font-semibold text-fg font-['Outfit']">
                          {item.title}
                        </span>
                        <span className="shrink-0 text-[10px] text-fg-faint">
                          {relativeTime(item.created_at)}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-fg-muted leading-relaxed line-clamp-2">
                        {item.message}
                      </p>
                    </div>

                    {/* Check if read */}
                    {!item.is_read ? (
                      <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/5 text-fg-faint transition-colors group-hover:bg-accent/20 group-hover:text-accent">
                        <Check className="h-3 w-3" />
                      </span>
                    ) : null}
                  </button>
                )
              })
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="border-t border-line/80 bg-surface/50 px-4 py-2.5 text-center text-[11px] text-fg-faint backdrop-blur-md">
              Showing recent alerts & updates
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
