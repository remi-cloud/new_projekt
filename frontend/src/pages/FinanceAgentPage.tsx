import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { useLocale } from '../context/LocaleContext'
import { GrowthFunnelStrip } from '../components/GrowthFunnelStrip'
import {
  fetchAiHistory,
  fetchAiStatus,
  postAiChat,
  postAiFeedback,
  postAiAnalyze,
  type AiChatResponse,
  type AiMessage,
  type AiStatus,
} from '../api'
import { formatThrownError, resolveApiMessage } from '../i18n/utils'

const SESSION_KEY = 'cyclical_ai_session'
const ROI_AGENT_SEED_KEY = 'cyclical_agent_roi_seed'

interface ChatEntry {
  id?: number
  role: 'user' | 'assistant'
  content: string
  meta?: Record<string, unknown>
}

export function FinanceAgentPage() {
  const { t, locale } = useLocale()
  const [status, setStatus] = useState<AiStatus | null>(null)
  const [sessionId, setSessionId] = useState<string>(() => localStorage.getItem(SESSION_KEY) || '')
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [symbol, setSymbol] = useState('BTC-USD')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastQuestion, setLastQuestion] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchAiStatus()
      .then(setStatus)
      .catch((err) => {
        setStatus(null)
        setError(formatThrownError(err, resolveApiMessage('fetchAiStatus')))
      })
  }, [])

  useEffect(() => {
    if (!sessionId) return
    fetchAiHistory(sessionId)
      .then((data) => {
        setMessages(
          data.messages.map((m: AiMessage) => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            meta: m.meta ?? undefined,
          })),
        )
      })
      .catch((err) => setError(formatThrownError(err, resolveApiMessage('aiHistoryFailed'))))
  }, [sessionId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const applyResponse = useCallback((res: AiChatResponse, question: string) => {
    if (res.session_id) {
      setSessionId(res.session_id)
      localStorage.setItem(SESSION_KEY, res.session_id)
    }
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question },
      {
        id: res.message_id,
        role: 'assistant',
        content: res.reply,
        meta: {
          tools_used: res.tools_used,
          critic_score: res.critic_score,
          llm_active: res.llm_active,
        },
      },
    ])
  }, [])

  const sendMessage = useCallback(
    async (text: string, sym?: string) => {
      const q = text.trim()
      if (!q || loading) return
      setError(null)
      setLoading(true)
      setLastQuestion(q)
      try {
        const res = await postAiChat({
          message: q,
          session_id: sessionId || undefined,
          locale,
          symbol: sym,
        })
        applyResponse(res, q)
        setInput('')
      } catch {
        setError(t('agent.errorSend'))
      } finally {
        setLoading(false)
      }
    },
    [applyResponse, loading, locale, sessionId, t],
  )

  useEffect(() => {
    const raw = sessionStorage.getItem(ROI_AGENT_SEED_KEY)
    if (!raw) return
    sessionStorage.removeItem(ROI_AGENT_SEED_KEY)
    try {
      const seed = JSON.parse(raw) as { message?: string; symbol?: string }
      if (seed.message) {
        if (seed.symbol) setSymbol(seed.symbol)
        void sendMessage(seed.message, seed.symbol)
      }
    } catch {
      /* ignore malformed seed */
    }
  }, [sendMessage])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    void sendMessage(input, symbol || undefined)
  }

  const handleQuick = (kind: 'trend' | 'pattern' | 'analyze' | 'cycles') => {
    const sym = symbol.trim() || 'BTC-USD'
    const prompts: Record<typeof kind, string> = {
      trend: t('agent.quickTrend').replace('{{symbol}}', sym),
      pattern: t('agent.quickPattern').replace('{{symbol}}', sym),
      analyze: t('agent.quickAnalyze').replace('{{symbol}}', sym),
      cycles: t('agent.quickCycles'),
    }
    void sendMessage(prompts[kind], kind === 'cycles' ? undefined : sym)
  }

  const handleAnalyzeOnly = async () => {
    const sym = symbol.trim()
    if (!sym || loading) return
    setError(null)
    setLoading(true)
    setLastQuestion(t('agent.analyzeOnly').replace('{{symbol}}', sym))
    try {
      const res = await postAiAnalyze(sym, locale)
      const fake: AiChatResponse = {
        session_id: sessionId,
        reply: res.summary,
        message_id: 0,
        tools_used: res.tools.map((t) => String(t.tool)),
        tool_results: res.tools,
        llm_active: res.llm_active,
        tool_count: res.tools.length,
      }
      applyResponse(fake, t('agent.analyzeOnly').replace('{{symbol}}', sym))
    } catch {
      setError(t('agent.errorAnalyze'))
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (messageId: number | undefined, rating: number) => {
    if (!sessionId) return
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
    try {
      await postAiFeedback({
        session_id: sessionId,
        message_id: messageId,
        rating,
        question: lastQuestion,
        answer: lastAssistant?.content,
      })
    } catch {
      /* ignore */
    }
  }

  const newSession = () => {
    setSessionId('')
    setMessages([])
    localStorage.removeItem(SESSION_KEY)
  }

  return (
    <div className="agent-page institutional-page">
      <header className="page-intro agent-header">
        <span className="page-eyebrow">{t('agent.eyebrow')}</span>
        <h2 className="page-headline">{t('agent.title')}</h2>
        <p className="page-lead">{t('agent.lead')}</p>
        {status && (
          <div className="agent-status-bar">
            <span className={`agent-badge ${status.llm_configured ? 'live' : 'local'}`}>
              {status.llm_configured ? t('agent.modeLlm') : t('agent.modeLocal')}
            </span>
            <span className="agent-meta">
              {t('agent.knowledge')}: {status.knowledge_entries} · {t('agent.learning')}: {status.learning_notes}
            </span>
          </div>
        )}
      </header>

      <div className="agent-toolbar">
        <label className="agent-symbol-field">
          <span>{t('agent.symbol')}</span>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="BTC-USD"
            className="agent-input-inline"
          />
        </label>
        <div className="agent-quick-actions">
          <button type="button" className="btn btn-ghost agent-quick-btn" onClick={() => handleQuick('trend')} disabled={loading}>
            {t('agent.btnTrend')}
          </button>
          <button type="button" className="btn btn-ghost agent-quick-btn" onClick={() => handleQuick('pattern')} disabled={loading}>
            {t('agent.btnPattern')}
          </button>
          <button type="button" className="btn btn-ghost agent-quick-btn" onClick={() => handleQuick('cycles')} disabled={loading}>
            {t('agent.btnCycles')}
          </button>
          <button type="button" className="btn btn-primary agent-quick-btn" onClick={handleAnalyzeOnly} disabled={loading}>
            {t('agent.btnAnalyze')}
          </button>
          <button type="button" className="btn btn-ghost agent-quick-btn" onClick={newSession} disabled={loading}>
            {t('agent.newChat')}
          </button>
        </div>
      </div>

      <div className="agent-chat-panel">
        <div className="agent-messages" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="agent-empty">
              <p>{t('agent.empty')}</p>
              <ul>
                <li>{t('agent.hintTrend')}</li>
                <li>{t('agent.hintPattern')}</li>
                <li>{t('agent.hintMacro')}</li>
              </ul>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={`${msg.id ?? i}-${msg.role}`} className={`agent-msg agent-msg-${msg.role}`}>
              <div className="agent-msg-role">{msg.role === 'user' ? t('agent.you') : t('agent.bot')}</div>
              <div className="agent-msg-body">{msg.content}</div>
              {msg.role === 'assistant' && msg.meta && (
                <div className="agent-msg-meta">
                  {Array.isArray(msg.meta.tools_used) && (msg.meta.tools_used as string[]).length > 0 && (
                    <span>{t('agent.tools')}: {(msg.meta.tools_used as string[]).join(', ')}</span>
                  )}
                  {typeof msg.meta.critic_score === 'number' && (
                    <span>{t('agent.critic')}: {Math.round((msg.meta.critic_score as number) * 100)}%</span>
                  )}
                  <div className="agent-feedback">
                    <button type="button" aria-label={t('agent.thumbsUp')} onClick={() => handleFeedback(msg.id, 5)}>
                      👍
                    </button>
                    <button type="button" aria-label={t('agent.thumbsDown')} onClick={() => handleFeedback(msg.id, 1)}>
                      👎
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="agent-msg agent-msg-assistant">
              <div className="agent-msg-role">{t('agent.bot')}</div>
              <div className="agent-msg-body agent-typing">{t('agent.thinking')}</div>
            </div>
          )}
        </div>

        {error && <p className="agent-error">{error}</p>}

        <form className="agent-composer" onSubmit={handleSubmit}>
          <textarea
            className="agent-textarea"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('agent.placeholder')}
            rows={2}
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void sendMessage(input, symbol || undefined)
              }
            }}
          />
          <button type="submit" className="btn btn-primary agent-send" disabled={loading || !input.trim()}>
            {loading ? t('agent.sending') : t('agent.send')}
          </button>
        </form>
      </div>

      <GrowthFunnelStrip source="agent" />

      <p className="agent-disclaimer">{t('agent.disclaimer')}</p>
    </div>
  )
}
