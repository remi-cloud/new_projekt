import { useLocale } from '../context/LocaleContext'

function formatSignalText(text: string, buy: string, sell: string) {
  const parts: (string | { type: 'buy' | 'sell' })[] = []
  const pattern = new RegExp(`(${buy}|${sell})`, 'gi')
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index))
    const matched = match[1]
    parts.push({ type: matched.toLowerCase() === buy.toLowerCase() ? 'buy' : 'sell' })
    lastIndex = match.index + matched.length
  }

  if (lastIndex < text.length) parts.push(text.slice(lastIndex))
  return parts
}

export function ConfidenceGuide() {
  const { t } = useLocale()
  const buy = t('labels.signal.buy')
  const sell = t('labels.signal.sell')
  const textParts = formatSignalText(t('confidence.text'), buy, sell)

  const formatPhaseDesc = (desc: string, signalLabel: string) => {
    const action = signalLabel.toUpperCase()
    return desc.replace(/\([^)]*\)/, `(${action})`)
  }

  return (
    <aside className="confidence-guide" aria-label={t('confidence.ariaLabel')}>
      <div className="confidence-guide-head">
        <span className="confidence-guide-title">{t('confidence.title')}</span>
        <span className="confidence-guide-badge">{t('confidence.badge')}</span>
      </div>
      <p className="confidence-guide-text">
        {textParts.map((part, i) =>
          typeof part === 'string' ? (
            <span key={i}>{part}</span>
          ) : (
            <strong key={i}>{part.type === 'buy' ? buy : sell}</strong>
          ),
        )}
      </p>
      <div className="confidence-guide-scale">
        <span className="conf-tier conf-tier-high">{t('confidence.tierHigh')}</span>
        <span className="conf-tier conf-tier-mid">{t('confidence.tierMid')}</span>
        <span className="conf-tier conf-tier-low">{t('confidence.tierLow')}</span>
      </div>
      <div className="phase-legend">
        <span className="tag phase-tag phase-bearish">{t('confidence.phaseBearish')}</span>
        <span className="phase-legend-desc">{formatPhaseDesc(t('confidence.phaseBearishDesc'), buy)}</span>
        <span className="tag phase-tag phase-bullish">{t('confidence.phaseBullish')}</span>
        <span className="phase-legend-desc">{formatPhaseDesc(t('confidence.phaseBullishDesc'), sell)}</span>
      </div>
    </aside>
  )
}
