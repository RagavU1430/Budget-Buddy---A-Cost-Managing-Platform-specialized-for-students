import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  GripVertical,
  Lock,
  Maximize2,
  Minimize2,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
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

const cleanContent = (text) => {
  if (!text) return ''
  return text.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*\*/g, '')
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
          className={`fixed bottom-4 z-50 flex h-[620px] max-h-[90vh] w-full max-w-[430px] flex-col overflow-hidden rounded-3xl border border-line-strong bg-surface-2/95 shadow-2xl backdrop-blur-2xl animate-[rise_0.3s_cubic-bezier(0.22,1,0.36,1)_both] ${
            position.x < (typeof window !== 'undefined' ? window.innerWidth / 2 : 500) ? 'left-4' : 'right-4'
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-line bg-surface/80 px-4 py-3.5 backdrop-blur-md">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent ring-1 ring-accent/30 shadow-sm">
                <Bot className="h-5 w-5" />
              </span>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-sm font-bold text-fg font-['Outfit']">BudgetBuddy AI</h3>
                  <span className="flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft/30 px-1.5 py-0.5 text-[10px] font-medium text-accent">
                    <ShieldCheck className="h-3 w-3" />
                    Guardrailed
                  </span>
                </div>
                <p className="text-[11px] text-fg-muted">Student Financial Intelligence Agent</p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleClear}
                title="Reset conversation"
                className="rounded-lg p-1.5 text-fg-faint hover:bg-white/5 hover:text-fg transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close chat"
                className="rounded-lg p-1.5 text-fg-faint hover:bg-white/5 hover:text-fg transition-colors"
              >
                <X className="h-4.5 w-4.5" />
              </button>
            </div>
          </div>

          {/* Quick prompts scroller */}
          <div className="border-b border-line/60 bg-surface/40 px-3 py-2 overflow-x-auto scrollbar-none flex items-center gap-2 shrink-0">
            <span className="text-[10px] uppercase font-bold text-fg-faint tracking-wider shrink-0 flex items-center gap-1">
              <Zap className="h-3 w-3 text-accent" />
              Ask:
            </span>
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(prompt)}
                className="shrink-0 rounded-full border border-line bg-white/4 px-2.5 py-1 text-[11px] font-medium text-fg-muted hover:border-accent/40 hover:bg-accent-soft/20 hover:text-fg transition-all cursor-pointer"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Messages list */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-sm">
            {messages.map((m) => {
              const isUser = m.role === 'user'
              const isGuardrail = m.guardrail_triggered || m.action_type === 'guardrail_blocked'

              return (
                <div
                  key={m.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed shadow-sm ${
                      isUser
                        ? 'bg-accent text-on-accent font-medium rounded-tr-sm'
                        : isGuardrail
                          ? 'border border-danger/40 bg-danger-soft text-fg rounded-tl-sm'
                          : 'border border-line bg-surface text-fg rounded-tl-sm'
                    }`}
                  >
                    {isGuardrail && (
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-danger mb-1.5">
                        <Lock className="h-3.5 w-3.5" />
                        <span>Security Guardrail</span>
                      </div>
                    )}
                    <div className="whitespace-pre-wrap">{cleanContent(m.content)}</div>

                    {m.action_type && m.action_type !== 'guardrail_blocked' && (
                      <div className="mt-2 inline-flex items-center gap-1 rounded border border-accent/30 bg-accent-soft/30 px-2 py-0.5 text-[10px] font-semibold text-accent">
                        <CheckCircle2 className="h-3 w-3" />
                        <span>Action Executed ({m.action_type})</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {loading && (
              <div className="flex items-start gap-2">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-2xl border border-line bg-surface px-4 py-2.5 text-xs text-fg-muted flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-accent animate-ping" />
                  <span>BudgetBuddy is calculating…</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input footer */}
          <div className="border-t border-line bg-surface/80 p-3 backdrop-blur-md">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSend()
              }}
              className="flex items-center gap-2"
            >
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask about your budget or type 'Spent 200 on books'..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                className="flex-1 rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-xs text-fg placeholder:text-fg-faint outline-none transition-all focus:border-accent focus:ring-1 focus:ring-accent/30"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent text-on-accent transition-all hover:bg-accent-hover hover:shadow-glow disabled:opacity-40 cursor-pointer"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
            <div className="mt-2 text-center text-[10px] text-fg-faint flex items-center justify-center gap-1">
              <Lock className="h-2.5 w-2.5 text-accent" />
              <span>Private & confidential. Passwords and session keys are never revealed.</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
