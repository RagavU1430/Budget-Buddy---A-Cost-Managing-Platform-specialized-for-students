import { Bus, GraduationCap, Lightbulb, ShoppingBag, Sparkles, UtensilsCrossed } from 'lucide-react'

// Vector icons + semantic tones — no emoji as structural icons (design rule).
export const EXPENSE_CATEGORIES = [
  { value: 'food', label: 'Food & Canteen', icon: UtensilsCrossed, tone: 'amber' },
  { value: 'travel', label: 'Travel & Metro', icon: Bus, tone: 'sky' },
  { value: 'education', label: 'Academic & Books', icon: GraduationCap, tone: 'violet' },
  { value: 'shopping', label: 'Shopping & Personal', icon: ShoppingBag, tone: 'rose' },
  { value: 'entertainment', label: 'Social & Fun', icon: Sparkles, tone: 'green' },
  { value: 'misc', label: 'Utilities & Misc', icon: Lightbulb, tone: 'neutral' },
]

export const PAYMENT_METHODS = [
  { value: 'upi', label: 'UPI' },
  { value: 'cash', label: 'Cash' },
  { value: 'card', label: 'Debit Card' },
  { value: 'bank', label: 'Net Banking' },
]

export const INCOME_SOURCES = [
  { value: 'pocket_money', label: 'Pocket Money' },
  { value: 'scholarship', label: 'Scholarship' },
  { value: 'part_time', label: 'Part-Time Job' },
  { value: 'freelance', label: 'Freelance' },
  { value: 'gift', label: 'Cash Gift' },
  { value: 'other', label: 'Other' },
]

export const categoryMeta = (value) => EXPENSE_CATEGORIES.find((c) => c.value === value)

export const toneClasses = {
  neutral: 'bg-white/6 text-fg-muted ring-line',
  green: 'bg-accent-soft text-accent ring-accent/30',
  rose: 'bg-danger-soft text-danger ring-danger/30',
  amber: 'bg-warn-soft text-warn ring-warn/30',
  violet: 'bg-[rgba(139,92,246,0.14)] text-violet-300 ring-violet-400/30',
  sky: 'bg-info-soft text-info ring-info/30',
}
