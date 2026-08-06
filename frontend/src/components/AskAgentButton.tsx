import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLocale } from '../context/LocaleContext'
import {
  instrumentAnalysisPrompt,
  newsAnalysisPrompt,
  seedAgentChat,
} from '../lib/agentSeed'

type NewsLike = {
  title: string
  summary?: string | null
  source?: string | null
  url?: string | null
  category?: string | null
}

type Props =
  | {
      mode: 'news'
      item: NewsLike
      symbol?: string
      className?: string
      compact?: boolean
    }
  | {
      mode: 'instrument'
      symbol: string
      name?: string
      className?: string
      compact?: boolean
      /** Optional extra context (e.g. Superokazje rationale) */
      extra?: string
    }

export function AskAgentButton(props: Props) {
  const navigate = useNavigate()
  const { t, locale } = useLocale()
  const label = props.mode === 'news' ? t('agent.analyzeNews') : t('agent.askAgent')

  const onClick = (e: MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (props.mode === 'news') {
      seedAgentChat({
        message: newsAnalysisPrompt(locale, props.item),
        symbol: props.symbol,
      })
    } else {
      const base = instrumentAnalysisPrompt(locale, props.symbol, props.name)
      const msg = props.extra?.trim()
        ? `${base}\n\nKontekst desk:\n${props.extra.trim().slice(0, 400)}`
        : base
      seedAgentChat({ message: msg, symbol: props.symbol })
    }
    navigate('/agent')
  }

  return (
    <button
      type="button"
      className={`ask-agent-btn tap-target${props.compact ? ' ask-agent-btn-compact' : ''}${props.className ? ` ${props.className}` : ''}`}
      onClick={onClick}
      title={label}
      aria-label={label}
    >
      <span className="ask-agent-ico" aria-hidden>
        AI
      </span>
      <span>{label}</span>
    </button>
  )
}
