import { useLocale } from '../context/LocaleContext'
import type { BrokerPurchaseInfo } from '../types'

interface BrokerPurchaseHintProps {
  info?: BrokerPurchaseInfo | null
  compact?: boolean
}

export function BrokerPurchaseHint({ info, compact = false }: BrokerPurchaseHintProps) {
  const { t } = useLocale()
  if (!info?.brokers?.length) return null

  return (
    <div className={`broker-hint ${compact ? 'broker-hint-compact' : ''}`}>
      {info.primary_exchange && (
        <div className="broker-hint-exchange">
          {t('broker.exchange')}: <strong>{info.primary_exchange}</strong>
        </div>
      )}
      <div className="broker-hint-label">{t('broker.buyVia')}</div>
      <ul className="broker-hint-list">
        {info.brokers.slice(0, compact ? 3 : 6).map((b) => (
          <li key={b.id}>
            <a href={b.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
              {b.name}
            </a>
            {!compact && b.notes ? <span className="broker-hint-notes"> — {b.notes}</span> : null}
          </li>
        ))}
      </ul>
      {!compact && info.disclaimer ? <p className="broker-hint-disclaimer">{info.disclaimer}</p> : null}
      {compact && <p className="broker-hint-disclaimer">{t('broker.disclaimerShort')}</p>}
    </div>
  )
}
