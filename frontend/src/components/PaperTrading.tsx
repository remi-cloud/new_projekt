import { useCallback, useEffect, useState } from 'react'
import { fetchPaperMaxBuy, fetchPaperPortfolio, placePaperOrder } from '../api'
import { PaperPortfolio as PaperPortfolioType } from '../types'
import { formatPln } from '../utils/format'

export function usePaperPortfolio(pollMs = 30_000) {
  const [portfolio, setPortfolio] = useState<PaperPortfolioType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const data = await fetchPaperPortfolio()
      setPortfolio(data)
      setError(null)
    } catch {
      setError('Nie udało się załadować portfela')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    reload()
    const t = setInterval(reload, pollMs)
    return () => clearInterval(t)
  }, [reload, pollMs])

  return { portfolio, loading, error, reload }
}

interface TradePanelProps {
  symbol: string
  name: string
  price: number
  onTrade?: () => void
}

export function TradePanel({ symbol, name, price, onTrade }: TradePanelProps) {
  const [mode, setMode] = useState<'qty' | 'pln'>('pln')
  const [quantity, setQuantity] = useState('')
  const [amountPln, setAmountPln] = useState('50000')
  const [maxQty, setMaxQty] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    fetchPaperMaxBuy(symbol).then((r) => setMaxQty(r.max_quantity)).catch(() => {})
  }, [symbol])

  const submit = async (side: 'buy' | 'sell') => {
    if (side === 'sell' && mode === 'pln') {
      setMsg('Sprzedaż: przełącz na zakładkę Ilość')
      return
    }
    setBusy(true)
    setMsg(null)
    try {
      const body =
        side === 'buy' && mode === 'pln'
          ? { symbol, side, amount_pln: parseFloat(amountPln) }
          : { symbol, side, quantity: parseFloat(quantity) }
      await placePaperOrder(body)
      setMsg(side === 'buy' ? 'Kupiono ✓' : 'Sprzedano ✓')
      onTrade?.()
    } catch (e) {
      const err = e as Error
      setMsg(err.message || 'Transakcja nieudana')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="trade-panel" onClick={(e) => e.stopPropagation()}>
      <h4>Paper trading — {name}</h4>
      <p className="trade-price-hint">Cena live: {price}</p>

      <div className="trade-mode-tabs">
        <button type="button" className={mode === 'pln' ? 'active' : ''} onClick={() => setMode('pln')}>
          Kwota PLN
        </button>
        <button type="button" className={mode === 'qty' ? 'active' : ''} onClick={() => setMode('qty')}>
          Ilość
        </button>
      </div>

      {mode === 'pln' ? (
        <label className="field-label">
          Kwota (PLN) — tylko kupno
          <input
            className="field-input"
            type="number"
            value={amountPln}
            onChange={(e) => setAmountPln(e.target.value)}
            min={1000}
            step={1000}
          />
        </label>
      ) : (
        <label className="field-label">
          Ilość {maxQty != null && `(max: ${maxQty})`}
          <input
            className="field-input"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            min={0}
            step="any"
            placeholder="np. 10"
          />
        </label>
      )}

      <div className="trade-actions">
        <button type="button" className="btn-buy tap-target" disabled={busy} onClick={() => submit('buy')}>
          Kupuj
        </button>
        <button type="button" className="btn-sell tap-target" disabled={busy} onClick={() => submit('sell')}>
          Sprzedaj
        </button>
      </div>
      {maxQty != null && mode === 'qty' && (
        <button
          type="button"
          className="btn-link tap-target"
          onClick={() => setQuantity(String(maxQty))}
        >
          Max ({maxQty})
        </button>
      )}
      {mode === 'pln' && (
        <div className="quick-amounts">
          {[10000, 50000, 100000, 250000].map((a) => (
            <button key={a} type="button" className="quick-amt" onClick={() => setAmountPln(String(a))}>
              {a / 1000}k
            </button>
          ))}
        </div>
      )}
      {msg && <p className="trade-msg">{msg}</p>}
    </div>
  )
}

export function PortfolioSummary({ portfolio }: { portfolio: PaperPortfolioType }) {
  const pnlClass = portfolio.total_pnl_pln >= 0 ? 'positive' : 'negative'
  return (
    <div className="portfolio-summary">
      <div className="portfolio-hero">
        <div className="stat-label">Wartość portfela</div>
        <div className="portfolio-equity">{formatPln(portfolio.total_equity_pln)}</div>
        <div className={`portfolio-pnl ${pnlClass}`}>
          {portfolio.total_pnl_pln >= 0 ? '+' : ''}
          {formatPln(portfolio.total_pnl_pln)} ({portfolio.total_pnl_pct}%)
        </div>
      </div>
      <div className="portfolio-stats-row">
        <div className="mini-stat">
          <span>Gotówka</span>
          <strong>{formatPln(portfolio.cash_pln)}</strong>
        </div>
        <div className="mini-stat">
          <span>Pozycje</span>
          <strong>{formatPln(portfolio.positions_value_pln)}</strong>
        </div>
        <div className="mini-stat">
          <span>USD/PLN</span>
          <strong>{portfolio.usd_pln_rate.toFixed(4)}</strong>
        </div>
      </div>
    </div>
  )
}
