import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import { GrowthFunnelStrip } from '../components/GrowthFunnelStrip'
import { AgentDeskCard } from '../components/AgentDeskCard'
import { focusSymbolFromMeta, toolResultsFromMeta } from '../components/AgentPatternChart'
import {
  fetchAiHistory,
  fetchAiStatus,
  fetchRoiAssets,
  postAiChat,
  postAiFeedback,
  postAiAnalyze,
  type AiChatResponse,
  type AiMessage,
  type AiStatus,
} from '../api'
import { formatThrownError, resolveApiMessage } from '../i18n/utils'
import { consumeAgentSeed, instrumentAnalysisPrompt } from '../lib/agentSeed'
import { resolveAgentSymbol } from '../lib/agentSymbol'

const SESSION_KEY = 'cyclical_ai_session'

interface ChatEntry {
  id?: number
  role: 'user' | 'assistant'
  content: string
  meta?: Record<string, unknown>
}

function normalizeHistoryMeta(meta?: Record<string, unknown> | null): Record<string, unknown> | undefined {
  if (!meta) return undefined
  const out: Record<string, unknown> = { ...meta }
  if (!Array.isArray(out.tools_used) && Array.isArray(out.tools)) {
    out.tools_used = out.tools
  }
  if (!Array.isArray(out.tool_results) && Array.isArray(out.tool_data)) {
    out.tool_results = out.tool_data
  }
  return out
}

function deskUiFromMeta(meta?: Record<string, unknown> | null): Record<string, unknown> | null {
  if (!meta) return null
  if (meta.desk_ui && typeof meta.desk_ui === 'object') return meta.desk_ui as Record<string, unknown>
  return null
}

export function FinanceAgentPage() {
  const { t, locale } = useLocale()
  const [searchParams, setSearchParams] = useSearchParams()
  const [status, setStatus] = useState<AiStatus | null>(null)
  const [sessionId, setSessionId] = useState<string>(() => localStorage.getItem(SESSION_KEY) || '')
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [symbol, setSymbol] = useState('BTC-USD')
  const [knownSymbols, setKnownSymbols] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastQuestion, setLastQuestion] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const seededRef = useRef(false)
  const skipNextHistoryRef = useRef(false)
  const symbolRef = useRef(symbol)
  const knownRef = useRef<string[]>([])
  const requestGenRef = useRef(0)

  useEffect(() => {
    symbolRef.current = symbol
  }, [symbol])

  useEffect(() => {
    knownRef.current = knownSymbols
  }, [knownSymbols])

  useEffect(() => {
    fetchAiStatus()
      .then(setStatus)
      .catch((err) => {
        setStatus(null)
        setError(formatThrownError(err, resolveApiMessage('fetchAiStatus')))
      })
    fetchRoiAssets()
      .then((assets) => setKnownSymbols(assets.map((a) => a.symbol)))
      .catch(() => setKnownSymbols([]))
  }, [])

  const canonicalizeToolbarSymbol = useCallback((): string | null => {
    const resolved = resolveAgentSymbol(symbolRef.current, knownRef.current)
    if (!resolved.ok) {
      if (resolved.reason === 'empty') setError(t('agent.emptySymbol'))
      else setError(t('agent.unknownSymbol', { symbol: resolved.input || symbolRef.current }))
      return null
    }
    if (resolved.symbol !== symbolRef.current.trim().toUpperCase().replace(/\s+/g, '')) {
      setSymbol(resolved.symbol)
      symbolRef.current = resolved.symbol
    } else {
      symbolRef.current = resolved.symbol
    }
    return resolved.symbol
  }, [t])

  useEffect(() => {
    if (!sessionId) return
    if (skipNextHistoryRef.current) {
      skipNextHistoryRef.current = false
      return
    }
    fetchAiHistory(sessionId)
      .then((data) => {
        setMessages(
          data.messages.map((m: AiMessage) => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            meta: normalizeHistoryMeta(m.meta),
          })),
        )
      })
      .catch((err) => setError(formatThrownError(err, resolveApiMessage('aiHistoryFailed'))))
  }, [sessionId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const applyResponse = useCallback(
    (res: AiChatResponse, question: string, requestedSymbol: string, gen: number) => {
      if (gen !== requestGenRef.current) return
      if (res.session_id) {
        // Skip one history wipe so live tool_results/SVG stay
        skipNextHistoryRef.current = true
        setSessionId(res.session_id)
        localStorage.setItem(SESSION_KEY, res.session_id)
      }
      // Toolbar symbol is user-owned — never overwrite from API focus_symbol.
      const lockedFocus = requestedSymbol || res.focus_symbol || null
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
            tool_results: res.tool_results,
            focus_symbol: lockedFocus,
            requested_symbol: requestedSymbol || undefined,
            desk_ui: res.desk_ui,
          },
        },
      ])
    },
    [],
  )

  const sendMessage = useCallback(
    async (text: string, sym?: string) => {
      const q = text.trim()
      if (!q || loading) return
      if (sym) {
        symbolRef.current = sym
      }
      const requested = canonicalizeToolbarSymbol()
      if (!requested) return
      const gen = ++requestGenRef.current
      setError(null)
      setLoading(true)
      setLastQuestion(q)
      try {
        const res = await postAiChat({
          message: q,
          session_id: sessionId || undefined,
          locale,
          symbol: requested,
        })
        applyResponse(res, q, requested, gen)
        setInput('')
      } catch {
        if (gen === requestGenRef.current) setError(t('agent.errorSend'))
      } finally {
        if (gen === requestGenRef.current) setLoading(false)
      }
    },
    [applyResponse, canonicalizeToolbarSymbol, loading, locale, sessionId, t],
  )

  useEffect(() => {
    if (seededRef.current || loading) return

    const seed = consumeAgentSeed()
    if (seed?.message) {
      seededRef.current = true
      if (seed.symbol) setSymbol(seed.symbol)
      void sendMessage(seed.message, seed.symbol)
      return
    }

    const qSym = searchParams.get('symbol')?.trim()
    const qMsg = searchParams.get('q')?.trim()
    const auto = searchParams.get('auto') === '1'
    if (qSym || qMsg) {
      seededRef.current = true
      if (qSym) setSymbol(qSym)
      const message = qMsg || (qSym ? instrumentAnalysisPrompt(locale, qSym) : '')
      if (message && (auto || qMsg)) {
        void sendMessage(message, qSym || undefined)
      } else if (qMsg) {
        setInput(qMsg)
      }
      setSearchParams({}, { replace: true })
    }
  }, [sendMessage, searchParams, setSearchParams, locale, loading])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    void sendMessage(input)
  }

  const handleQuick = (kind: 'trend' | 'pattern' | 'analyze' | 'cycles') => {
    const sym = canonicalizeToolbarSymbol()
    if (!sym) return
    const prompts: Record<typeof kind, string> = {
      trend: t('agent.quickTrend').replace('{{symbol}}', sym),
      pattern: t('agent.quickPattern').replace('{{symbol}}', sym),
      analyze: t('agent.quickAnalyze').replace('{{symbol}}', sym),
      cycles: t('agent.quickCycles'),
    }
    // Always pass toolbar symbol — including Cycles — so focus cannot jump.
    void sendMessage(prompts[kind], sym)
  }

  const handleAnalyzeOnly = async () => {
    if (loading) return
    const sym = canonicalizeToolbarSymbol()
    if (!sym) return
    const gen = ++requestGenRef.current
    setError(null)
    setLoading(true)
    setLastQuestion(t('agent.analyzeOnly').replace('{{symbol}}', sym))
    try {
      const res = await postAiAnalyze(sym, locale)
      const fake: AiChatResponse = {
        session_id: sessionId,
        reply: res.summary,
        message_id: 0,
        tools_used: res.tools.map((x) => String(x.tool)),
        tool_results: res.tools,
        llm_active: res.llm_active,
        tool_count: res.tools.length,
        focus_symbol: sym,
        desk_ui: res.desk_ui,
      }
      applyResponse(fake, t('agent.analyzeOnly').replace('{{symbol}}', sym), sym, gen)
    } catch {
      if (gen === requestGenRef.current) setError(t('agent.errorAnalyze'))
    } finally {
      if (gen === requestGenRef.current) setLoading(false)
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
    skipNextHistoryRef.current = false
    setSessionId('')
    setMessages([])
    localStorage.removeItem(SESSION_KEY)
  }

  const deskLabels = {
    patternChart: t('agent.patternChart'),
    openInstrument: t('agent.openInstrument'),
    deskBias: t('agent.deskBias'),
    deskLevels: t('agent.deskLevels'),
    deskRisk: t('agent.deskRisk'),
    analyzingSymbol: t('agent.analyzingSymbol'),
    deskMtf: t('agent.deskMtf'),
    deskPatterns: t('agent.deskPatterns'),
    deskThesis: t('agent.deskThesis'),
    deskCouncil: t('agent.deskCouncil'),
    deskSetup: t('agent.deskSetup'),
    deskPlan: t('agent.deskPlan'),
    deskAnalysis: t('agent.deskAnalysis'),
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
              {status.provider && status.provider !== 'none' ? `${status.provider} · ${status.model}` : status.model}
              {' · '}
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
            list="agent-symbol-catalog"
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            onBlur={() => {
              const resolved = resolveAgentSymbol(symbolRef.current, knownRef.current)
              if (resolved.ok && resolved.symbol !== symbol) setSymbol(resolved.symbol)
            }}
            placeholder="LQD / BTC-USD / SPCX"
            className="agent-input-inline"
            disabled={loading}
            autoComplete="off"
            spellCheck={false}
          />
          <datalist id="agent-symbol-catalog">
            {knownSymbols.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
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
          {messages.map((msg, i) => {
            const hasDesk =
              msg.role === 'assistant' &&
              (Boolean(focusSymbolFromMeta(msg.meta)) ||
                Boolean(deskUiFromMeta(msg.meta)) ||
                Boolean(toolResultsFromMeta(msg.meta)) ||
                Boolean(msg.content))
            return (
              <div key={`${msg.id ?? i}-${msg.role}`} className={`agent-msg agent-msg-${msg.role}`}>
                <div className="agent-msg-role">{msg.role === 'user' ? t('agent.you') : t('agent.bot')}</div>
                {msg.role === 'user' && <div className="agent-msg-body">{msg.content}</div>}
                {msg.role === 'assistant' && hasDesk && (
                  <AgentDeskCard
                    requestedSymbol={
                      (typeof msg.meta?.requested_symbol === 'string' && msg.meta.requested_symbol) ||
                      focusSymbolFromMeta(msg.meta)
                    }
                    focusSymbol={focusSymbolFromMeta(msg.meta)}
                    toolResults={toolResultsFromMeta(msg.meta)}
                    deskUi={deskUiFromMeta(msg.meta)}
                    reply={msg.content}
                    labels={deskLabels}
                  />
                )}
                {msg.role === 'assistant' && msg.meta && (
                  <div className="agent-msg-meta">
                    {(typeof msg.meta.requested_symbol === 'string' ||
                      typeof msg.meta.focus_symbol === 'string') && (
                      <span>
                        {t('agent.analyzingSymbol').replace(
                          '{{symbol}}',
                          String(msg.meta.requested_symbol || msg.meta.focus_symbol),
                        )}
                      </span>
                    )}
                    {typeof msg.meta.critic_score === 'number' && (
                      <span>
                        {t('agent.critic')}:{' '}
                        {Math.round(
                          (msg.meta.critic_score as number) <= 1
                            ? (msg.meta.critic_score as number) * 100
                            : (msg.meta.critic_score as number),
                        )}
                        %
                      </span>
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
            )
          })}
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
                void sendMessage(input)
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
