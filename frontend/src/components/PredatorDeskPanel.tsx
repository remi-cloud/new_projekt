import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchPredatorSignals,
  fetchPredatorStatus,
  pollPredatorFeed,
  type PredatorSignal,
  type PredatorStatus,
} from '../api'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import { QuickTradeButtons } from './QuickTradeButtons'

export function PredatorDeskPanel() {
  const { t, dateLocale } = useLocale()
  const [status, setStatus] = useState<PredatorStatus | null>(null)
  const [signals, setSignals] = useState<PredatorSignal[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const reload = useCallback(async () => {
    const [st, sig] = await Promise.all([fetchPredatorStatus(), fetchPredatorSignals(20)])
    setStatus(st)
    setSignals(sig.signals)
  }, [])

  useEffect(() => {
    reload().catch(() => setMsg(t('alerts.loadError')))
  }, [reload, t])

  const onPoll = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const r = await pollPredatorFeed()
      setMsg(t('predator.pollOk', { updates: r.updates, n: r.new }))
      await reload()
    } catch (e) {
      setMsg(formatThrownError(e, t('predator.pollFail')))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="settings-card predator-desk" aria-label="Telegram Predator">
      <h3>{t('predator.title')}</h3>
      <p className="page-lead">{t('predator.lead')}</p>
      <p className="cell-sub">
        {status?.configured
          ? t('predator.configured', { bot: status.bot?.username || 'bot' })
          : t('predator.needToken')}
      </p>
      <div className="predator-actions">
        <button type="button" className="btn-secondary tap-target" disabled={busy} onClick={() => void onPoll()}>
          {busy ? '…' : t('predator.poll')}
        </button>
        <a className="btn btn-ghost tap-target" href="https://t.me/BotFather" target="_blank" rel="noreferrer">
          BotFather
        </a>
      </div>
      {msg && <p className="settings-message">{msg}</p>}
      <ul className="predator-signal-list">
        {signals.length === 0 && <li className="empty-state">{t('predator.empty')}</li>}
        {signals.map((s) => (
          <li key={s.id} className="predator-signal-row">
            <div>
              <Link to={`/instrument/${encodeURIComponent(s.symbol)}`}>
                <strong>{s.symbol}</strong>
              </Link>{' '}
              <span className={`signal-tag signal-${s.action === 'buy' ? 'buy' : s.action === 'sell' ? 'sell' : 'watch'}`}>
                {s.action}
              </span>
              <div className="cell-sub">{new Date(s.created_at).toLocaleString(dateLocale)}</div>
              <p className="opp-rationale">{s.reason}</p>
            </div>
            <QuickTradeButtons symbol={s.symbol} compact />
          </li>
        ))}
      </ul>
    </section>
  )
}
