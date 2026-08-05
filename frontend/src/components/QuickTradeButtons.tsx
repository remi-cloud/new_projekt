import { useContext, useState } from 'react'
import { placePaperOrder } from '../api'
import { DashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'

const DEFAULT_PLN = 10_000

interface QuickTradeButtonsProps {
  symbol: string
  /** Paper order size in PLN (market). */
  amountPln?: number
  onTrade?: () => void
  compact?: boolean
}

/** Inline Kup / Sprzedaj → paper portfolio (market order). */
export function QuickTradeButtons({
  symbol,
  amountPln = DEFAULT_PLN,
  onTrade,
  compact = false,
}: QuickTradeButtonsProps) {
  const { t } = useLocale()
  const desk = useContext(DashboardContext)
  const [busy, setBusy] = useState<'buy' | 'sell' | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const submit = async (side: 'buy' | 'sell') => {
    setBusy(side)
    setMsg(null)
    try {
      await placePaperOrder({
        symbol,
        side,
        amount_pln: amountPln,
        order_type: 'market',
      })
      setMsg(side === 'buy' ? t('paper.bought') : t('paper.sold'))
      await desk?.reloadPortfolio?.()
      onTrade?.()
    } catch (e) {
      setMsg(formatThrownError(e, t('paper.tradeFailed')))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div
      className={`quick-trade ${compact ? 'compact' : ''}`}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <div className="quick-trade-actions">
        <button
          type="button"
          className="btn-buy tap-target"
          disabled={busy !== null}
          onClick={() => void submit('buy')}
        >
          {busy === 'buy' ? '…' : t('paper.buy')}
        </button>
        <button
          type="button"
          className="btn-sell tap-target"
          disabled={busy !== null}
          onClick={() => void submit('sell')}
        >
          {busy === 'sell' ? '…' : t('paper.sell')}
        </button>
      </div>
      {msg && <p className={`quick-trade-msg${msg.includes('✓') ? ' ok' : ''}`}>{msg}</p>}
    </div>
  )
}
