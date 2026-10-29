import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  GripVertical,
  Lock,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  User,
  X,
  Zap,
} from 'lucide-react'

import { clearChatHistory, getChatHistory, sendChatMessage } from '../api/assistant.js'

const QUICK_PROMPTS = [
  'What is my safe daily spending rate?',
  'How much have I spent this month?',
  'How is my food budget doing?',
  'Log expense 120 on canteen lunch',
  'Give me student saving tips',
]

const ACTION_LABELS = {
  expense_created: {
    label: 'Expense Logged Successfully',
    bg: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  },
  budget_created: {
    label: 'Budget Limit Updated',
    bg: 'bg-accent/15 text-accent border-accent/30',
  },
  income_created: {
    label: 'Income Recorded',
    bg: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  },
}

const cleanContent = (text) => {
  if (!text) return ''
  return text.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*\*/g, '')
}

function FormattedMessage({ content }) {
  const lines = cleanContent(content).split('\n')
  return (
    <div className="space-y-1.5 text-[13px] leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim()
        if (!trimmed) {
          return <div key={idx} className="h-1" />
        }

        // Bullet point
        if (trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*')) {
          const textWithoutBullet = trimmed.replace(/^[•\-*]\s*/, '')
          const colonMatch = textWithoutBullet.match(/^([^:]+):(.*)$/)
          if (colonMatch) {
            return (
              <div key={idx} className="flex items-start gap-2 text-fg/90">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                <span>
                  <strong className="font-semibold text-fg">{colonMatch[1]}:</strong>
                  <span className="text-fg-muted">{colonMatch[2]}</span>
                </span>
              </div>
            )
          }
          return (
            <div key={idx} className="flex items-start gap-2 text-fg-muted">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span>{textWithoutBullet}</span>
            </div>
          )
        }

        // Section header with emoji (e.g. "💡 Next Steps for You")
        if (/^[\p{Emoji}\u200d\uFE0F]/u.test(trimmed) && trimmed.length < 50) {
          return (
            <div key={idx} className="font-semibold text-fg text-sm pt-1.5 pb-0.5 flex items-center gap-1.5 text-accent">
              <span>{trimmed}</span>
            </div>
          )
        }

        return (
          <p key={idx} className="text-fg/90">
            {trimmed}
          </p>
        )
      })}
    </div>
  )
}

export default function BudgetAssistantWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [initialLoaded, setInitialLoaded] = useState(false)

  // Drag-and-drop state
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem('budgetbuddy_ai_pos')
      if (saved) {
        const parsed = JSON.parse(saved)
        if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
          return parsed
        }
      }
    } catch {}
    if (typeof window !== 'undefined') {
      return {
        x: Math.max(16, window.innerWidth - 290),
        y: Math.max(16, window.innerHeight - 84),
      }
    }
    return { x: 20, y: 100 }
  })

  const isDraggingRef = useRef(false)
  const dragStartRef = useRef({ startX: 0, startY: 0, initialX: 0, initialY: 0 })
  const hasMovedRef = useRef(false)
  const currentPosRef = useRef(position)
  const [isDraggingState, setIsDraggingState] = useState(false)

  useEffect(() => {
    currentPosRef.current = position
  }, [position])

  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => {
        const buttonWidth = 270
        const buttonHeight = 70
        const nextX = Math.min(Math.max(12, prev.x), Math.max(12, window.innerWidth - buttonWidth))
        const nextY = Math.min(Math.max(12, prev.y), Math.max(12, window.innerHeight - buttonHeight))
        return { x: nextX, y: nextY }
      })
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const handlePointerDown = (e) => {
    if (e.button !== 0 && e.pointerType === 'mouse') return
    isDraggingRef.current = true
    hasMovedRef.current = false
    dragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialX: position.x,
      initialY: position.y,
    }
    setIsDraggingState(true)
    try {
      e.currentTarget.setPointerCapture(e.pointerId)
    } catch {}
  }

  const handlePointerMove = (e) => {
    if (!isDraggingRef.current) return
    const dx = e.clientX - dragStartRef.current.startX
    const dy = e.clientY - dragStartRef.current.startY
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
      hasMovedRef.current = true
    }
    const buttonWidth = 270
    const buttonHeight = 70
    const nextX = Math.min(Math.max(8, dragStartRef.current.initialX + dx), Math.max(8, window.innerWidth - buttonWidth))
    const nextY = Math.min(Math.max(8, dragStartRef.current.initialY + dy), Math.max(8, window.innerHeight - buttonHeight))
    const nextPos = { x: nextX, y: nextY }
    currentPosRef.current = nextPos
    setPosition(nextPos)
  }

  const handlePointerUp = (e) => {
    if (!isDraggingRef.current) return
    isDraggingRef.current = false
    setIsDraggingState(false)
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {}

    if (!hasMovedRef.current) {
      setIsOpen(true)
    } else {
      try {
        localStorage.setItem('budgetbuddy_ai_pos', JSON.stringify(currentPosRef.current))
      } catch {}
    }
  }

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen && !initialLoaded) {
      getChatHistory()
        .then((res) => {
          if (res?.messages?.length) {
            setMessages(res.messages)
          } else {
            setMessages([
              {
                id: 'welcome',
                role: 'assistant',
                content:
                  "👋 Hello! I am BudgetBuddy AI, your personal student financial advisor powered by Gemini.\n\nAsk me about your daily allowances, monthly expenses, budget limits, or type commands like 'Spent 150 on food' to automatically record transactions.\n\n🔒 Strict Privacy: I only have access to your personal budget data and will never expose passwords, tokens, or system IDs.",
              },
            ])
          }
          setInitialLoaded(true)
        })
        .catch(() => {
          setInitialLoaded(true)
        })
    }
  }, [isOpen, initialLoaded])

  useEffect(() => {
    if (isOpen) {
      scrollToBottom()
      setTimeout(() => inputRef.current?.focus(), 150)
    }
  }, [isOpen, messages])

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim()
    if (!text || loading) return

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, tempUserMsg])
    setInput('')
    setLoading(true)

    try {
      const data = await sendChatMessage(text)
      const botMsg = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: data.reply,
        action_type: data.action_type,
        action_data: data.action_data,
        guardrail_triggered: data.guardrail_triggered,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, botMsg])

      // If an actionable command modified the database (budget, expense, income), notify UI components to re-fetch live data
      if (
        data.action_type &&
        !['gemini_response', 'guardrail_blocked', 'error'].includes(data.action_type)
      ) {
        window.dispatchEvent(new CustomEvent('budgetbuddy:data-refresh', { detail: data }))
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: '⚠️ Failed to reach BudgetBuddy AI. Please check your backend connection.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    try {
      await clearChatHistory()
      setMessages([
        {
          id: 'cleared',
          role: 'assistant',
          content: '🧹 Chat history has been reset. How can I help you with your budget today?',
        },
      ])
    } catch {
      // ignore
    }
  }

  return (
    <>
      {/* Movable floating launcher trigger */}
      {!isOpen && (
        <div
          role="button"
          tabIndex={0}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              setIsOpen(true)
            }
          }}
          style={{
            left: `${position.x}px`,
            top: `${position.y}px`,
          }}
          className={`fixed z-50 flex items-center gap-2 rounded-full border border-accent/40 bg-surface/90 px-3.5 py-2.5 text-sm font-semibold text-fg shadow-2xl backdrop-blur-xl transition-[border-color,box-shadow,transform] duration-200 hover:border-accent hover:shadow-glow cursor-grab active:cursor-grabbing select-none touch-none group ${
            isDraggingState ? 'scale-105 shadow-glow ring-2 ring-accent/40 opacity-95' : ''
          }`}
          aria-label="Open BudgetBuddy AI Assistant (Drag to move)"
          title="Drag anywhere to reposition, click to open"
        >
          <GripVertical className="h-4 w-4 text-fg-faint group-hover:text-fg-muted transition-colors -mr-0.5 shrink-0" />
          <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-accent text-on-accent shadow-sm shrink-0">
            <Sparkles className="h-4 w-4 transition-transform group-hover:rotate-12" />
            <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-surface animate-ping" />
          </span>
          <div className="text-left pr-1">
            <div className="text-xs font-bold font-['Outfit'] text-fg flex items-center gap-1">
              <span>BudgetBuddy AI</span>
              <span className="rounded bg-accent/20 px-1 py-0.2 text-[9px] text-accent">Active</span>
            </div>
            <div className="text-[10px] text-fg-muted">Ask anything about your budget</div>
          </div>
        </div>
      )}

      {/* Slide-out / floating chat drawer */}
      {isOpen && (
        <div
          className={`fixed bottom-4 z-50 flex h-[640px] max-h-[92vh] w-full max-w-[440px] flex-col overflow-hidden rounded-[2rem] border border-line-strong bg-[#090D1C]/95 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)] ring-1 ring-white/10 backdrop-blur-2xl animate-[rise_0.3s_cubic-bezier(0.22,1,0.36,1)_both] ${
            position.x < (typeof window !== 'undefined' ? window.innerWidth / 2 : 500) ? 'left-4' : 'right-4'
          }`}
        >
          {/* Header */}
          <div className="relative flex items-center justify-between border-b border-line-strong/60 bg-[#0E1428]/85 px-4.5 py-3.5 backdrop-blur-xl">
            {/* Ambient accent glow in header */}
            <div className="pointer-events-none absolute -left-6 -top-6 h-28 w-28 rounded-full bg-accent/20 blur-xl" />

            <div className="relative flex items-center gap-3">
              <div className="relative flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-accent/25 to-teal-500/10 text-accent ring-1 ring-accent/30 shadow-sm">
                <Bot className="h-5 w-5" />
                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-[#0E1428]" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-sm font-bold text-fg font-['Outfit'] tracking-tight">BudgetBuddy AI</h3>
                  <span className="flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft/40 px-2 py-0.5 text-[10px] font-semibold text-accent">
                    <ShieldCheck className="h-3 w-3" />
                    Guardrailed
                  </span>
                </div>
                <p className="text-[11px] text-fg-muted">Financial Intelligence Assistant</p>
              </div>
            </div>

            <div className="relative flex items-center gap-1">
              <button
                type="button"
                onClick={handleClear}
                title="Reset conversation"
                className="flex h-8 w-8 items-center justify-center rounded-xl text-fg-faint hover:bg-white/5 hover:text-danger transition-colors cursor-pointer"
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close chat"
                className="flex h-8 w-8 items-center justify-center rounded-xl text-fg-faint hover:bg-white/5 hover:text-fg transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Quick prompts scroller — Hidden scrollbars for clean look */}
          <div className="border-b border-line/60 bg-[#0A0E20]/70 px-3.5 py-2.5 flex items-center gap-2 shrink-0 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <span className="text-[10px] uppercase font-bold text-fg-faint tracking-wider shrink-0 flex items-center gap-1">
              <Zap className="h-3 w-3 text-accent" />
              Ask:
            </span>
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(prompt)}
                className="shrink-0 rounded-full border border-line bg-white/4 px-3 py-1 text-[11px] font-medium text-fg-muted hover:border-accent/50 hover:bg-accent-soft/20 hover:text-fg hover:scale-[1.02] transition-all cursor-pointer select-none"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Messages list — Modern slim custom scrollbar */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 text-sm [scrollbar-width:thin] [scrollbar-color:rgba(148,163,184,0.2)_transparent] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-white/10 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-white/20">
            {messages.map((m) => {
              const isUser = m.role === 'user'
              const isGuardrail = m.guardrail_triggered || m.action_type === 'guardrail_blocked'
              const actionMeta = ACTION_LABELS[m.action_type]

              return (
                <div
                  key={m.id}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start items-start gap-2.5'}`}
                >
                  {!isUser && (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent/20 to-teal-500/20 text-accent ring-1 ring-accent/30 shadow-sm mt-0.5">
                      <Sparkles className="h-3.5 w-3.5" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl p-3.5 text-[13px] leading-relaxed shadow-sm transition-all ${
                      isUser
                        ? 'rounded-tr-sm bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-medium shadow-[0_4px_16px_rgba(16,185,129,0.25)]'
                        : isGuardrail
                          ? 'rounded-tl-sm border border-danger/40 bg-danger-soft/90 text-fg'
                          : 'rounded-tl-sm border border-line-strong/60 bg-[#0E1428]/90 text-fg shadow-[0_4px_20px_rgba(0,0,0,0.3)] backdrop-blur-md'
                    }`}
                  >
                    {isGuardrail && (
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-danger mb-1.5">
                        <Lock className="h-3.5 w-3.5" />
                        <span>Security Guardrail</span>
                      </div>
                    )}

                    {isUser ? (
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    ) : (
                      <FormattedMessage content={m.content} />
                    )}

                    {/* Only show real action executions like expense_created, budget_created, income_created */}
                    {actionMeta && (
                      <div
                        className={`mt-2.5 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${actionMeta.bg}`}
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        <span>{actionMeta.label}</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {loading && (
              <div className="flex items-start gap-2.5">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent ring-1 ring-accent/30 shadow-sm">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-2xl rounded-tl-sm border border-line-strong/60 bg-[#0E1428]/90 px-4 py-2.5 text-xs text-fg-muted flex items-center gap-2 shadow-sm">
                  <span className="flex gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                  <span>BudgetBuddy is calculating…</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input footer */}
          <div className="border-t border-line-strong/60 bg-[#0E1428]/90 p-3.5 backdrop-blur-xl">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSend()
              }}
              className="flex items-center gap-2"
            >
              <div className="relative flex-1 flex items-center rounded-2xl border border-line-strong bg-white/4 px-3.5 py-2.5 transition-all focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Ask anything or type 'Spent 150 on food'..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  className="w-full bg-transparent text-xs text-fg placeholder:text-fg-faint outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all hover:scale-105 active:scale-95 disabled:opacity-40 disabled:hover:scale-100 cursor-pointer"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
            <div className="mt-2 text-center text-[10px] text-fg-faint flex items-center justify-center gap-1.5">
              <Lock className="h-2.5 w-2.5 text-accent" />
              <span>Grounded in your budget data · Private & confidential</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
