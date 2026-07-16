import { useState } from 'react'
import type { RoiCalculateResult } from '../types'
import { useLocale } from '../context/LocaleContext'

type Props = { result: RoiCalculateResult }

export function RoiShareCard({ result }: Props) {
  const { t, dateLocale } = useLocale()
  const [copied, setCopied] = useState(false)
  const isForward = result.mode === 'forward'
  const text = isForward
    ? `${result.name}: ${result.amount.toLocaleString(dateLocale)} USD → ${result.final_value.toLocaleString(dateLocale)} USD in ${result.years}y (${result.roi_pct.toFixed(0)}% ROI) · kar digital Cyclical Academy`
    : `${result.name} backtest: ${result.roi_pct.toFixed(0)}% ROI · kar digital`

  const shareUrl = `${window.location.origin}/kalkulator`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${text}\n${shareUrl}`)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* ignore */
    }
  }

  const tweet = () => {
    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`,
      '_blank',
      'noopener,noreferrer',
    )
  }

  return (
    <div className="roi-share-card">
      <div className="roi-share-visual">
        <span className="roi-share-brand">kar digital · Cyclical Academy</span>
        <strong>{result.name}</strong>
        <p>
          {isForward
            ? `${result.amount.toLocaleString(dateLocale)} → ${result.final_value.toLocaleString(dateLocale)}`
            : `${result.roi_pct.toFixed(1)}% ROI`}
        </p>
        <small>
          {isForward ? `${result.years}y · ${result.strategy}` : result.strategy}
          {result.buy_hold ? ` · B&H ${result.buy_hold.roi_pct.toFixed(0)}%` : ''}
        </small>
      </div>
      <div className="roi-share-actions">
        <button type="button" className="btn tap-target" onClick={() => void copy()}>
          {copied ? t('growth.copied') : t('growth.copyEmbed')}
        </button>
        <button type="button" className="btn btn-ghost tap-target" onClick={tweet}>
          Share X
        </button>
      </div>
    </div>
  )
}
