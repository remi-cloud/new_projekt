import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { calculateRoi, fetchRoiAssets } from '../api'
import { ErrorState } from '../components/Loading'
import { RoiEquityChart } from '../components/RoiEquityChart'
import { RoiShareCard } from '../components/RoiShareCard'
import { GrowthFunnelStrip } from '../components/GrowthFunnelStrip'
import { useLocale } from '../context/LocaleContext'
import type { RoiAssetInfo, RoiCalculateResult, RoiMode, RoiStrategy } from '../types'

const STRATEGIES: RoiStrategy[] = ['buy_hold', 'cycle', 'dca', 'cycle_dca']
const ROI_AGENT_SEED_KEY = 'cyclical_agent_roi_seed'

function fmtMoney(n: number, locale: string): string {
  return n.toLocaleString(locale, { maximumFractionDigits: 0 })
}

function fmtPct(n: number): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

export function RoiCalculatorPage() {
  const { t, dateLocale, locale } = useLocale()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [assets, setAssets] = useState<RoiAssetInfo[]>([])
  const [mode, setMode] = useState<RoiMode>('forward')
  const [symbol, setSymbol] = useState('BTC-USD')
  const [amount, setAmount] = useState(10000)
  const [years, setYears] = useState(30)
  const [monthly, setMonthly] = useState(0)
  const [strategy, setStrategy] = useState<RoiStrategy>('buy_hold')
  const [start, setStart] = useState('2015-01-01')
  const [loadingAssets, setLoadingAssets] = useState(true)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [assetsError, setAssetsError] = useState(false)
  const [result, setResult] = useState<RoiCalculateResult | null>(null)
  const resultsRef = useRef<HTMLElement>(null)
  const autoRanRef = useRef(false)

  const loadAssets = useCallback(async () => {
    setLoadingAssets(true)
    setAssetsError(false)
    try {
      const list = await fetchRoiAssets()
      setAssets(list)
      if (list.length && !list.find((a) => a.symbol === 'BTC-USD')) {
        setSymbol(list[0].symbol)
      }
    } catch {
      setAssetsError(true)
      setError(t('roi.errors.assets'))
    } finally {
      setLoadingAssets(false)
    }
  }, [t])

  useEffect(() => {
    void loadAssets()
  }, [loadAssets])

  const runCalculate = useCallback(
    async (overrides?: { symbol?: string; mode?: RoiMode }) => {
      const sym = overrides?.symbol ?? symbol
      const calcMode = overrides?.mode ?? mode
      setCalculating(true)
      setError(null)
      try {
        const data = await calculateRoi({
          symbol: sym,
          amount,
          strategy,
          mode: calcMode,
          years,
          monthly_contribution: monthly,
          start: calcMode === 'backtest' ? start || undefined : undefined,
          compare_buy_hold: true,
        })
        setResult(data)
        window.setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 120)
      } catch {
        setError(t('roi.errors.calculate'))
      } finally {
        setCalculating(false)
      }
    },
    [amount, mode, monthly, start, strategy, symbol, t, years],
  )

  const onSubmit = async (e?: FormEvent) => {
    e?.preventDefault()
    await runCalculate()
  }

  useEffect(() => {
    const qpMode = searchParams.get('mode')
    const qpSymbol = searchParams.get('symbol')
    if (qpMode === 'backtest' || qpMode === 'forward') setMode(qpMode)
    if (qpSymbol) setSymbol(qpSymbol)
  }, [searchParams])

  useEffect(() => {
    const qpMode = searchParams.get('mode')
    const qpSymbol = searchParams.get('symbol')
    if (qpMode !== 'backtest' || autoRanRef.current || loadingAssets || assetsError) return
    autoRanRef.current = true
    void runCalculate({ symbol: qpSymbol || symbol, mode: 'backtest' })
  }, [searchParams, loadingAssets, assetsError, runCalculate, symbol])

  const selected = useMemo(() => assets.find((a) => a.symbol === symbol), [assets, symbol])
  const isForward = mode === 'forward'

  const onSymbolChange = (sym: string) => {
    setSymbol(sym)
    const asset = assets.find((a) => a.symbol === sym)
    if (asset?.history_from) setStart(asset.history_from)
  }

  const explainWithAgent = (res: RoiCalculateResult) => {
    const bh = res.buy_hold ? ` Buy&Hold ROI ${res.buy_hold.roi_pct.toFixed(1)}%.` : ''
    const seed =
      locale === 'pl'
        ? `Wyjaśnij wynik backtestu ROI: ${res.name} (${res.symbol}), strategia ${res.strategy}, kwota ${res.amount} USD, wartość końcowa ${res.final_value} USD, zysk ${res.profit} USD, ROI ${res.roi_pct.toFixed(1)}%, CAGR ${res.cagr_pct.toFixed(1)}%.${bh} Co oznaczają fazy cyklu w tym wyniku?`
        : `Explain this ROI backtest: ${res.name} (${res.symbol}), strategy ${res.strategy}, amount ${res.amount} USD, final ${res.final_value} USD, profit ${res.profit} USD, ROI ${res.roi_pct.toFixed(1)}%, CAGR ${res.cagr_pct.toFixed(1)}%.${bh} What do the cycle phases mean here?`
    sessionStorage.setItem(ROI_AGENT_SEED_KEY, JSON.stringify({ message: seed, symbol: res.symbol }))
    navigate('/agent')
  }

  if (loadingAssets && !assets.length) {
    return <div className="page-loading">{t('roi.loading')}</div>
  }

  return (
    <div className="roi-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">{t('roi.eyebrow')}</span>
        <h2 className="page-headline">{t('roi.headline')}</h2>
        <p className="page-lead">{t('roi.lead')}</p>
      </header>

      <div className="roi-mode-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          className={`roi-mode-tab ${mode === 'forward' ? 'active' : ''}`}
          aria-selected={mode === 'forward'}
          onClick={() => setMode('forward')}
        >
          {t('roi.modeForward')}
        </button>
        <button
          type="button"
          role="tab"
          className={`roi-mode-tab ${mode === 'backtest' ? 'active' : ''}`}
          aria-selected={mode === 'backtest'}
          onClick={() => setMode('backtest')}
        >
          {t('roi.modeBacktest')}
        </button>
      </div>
      <p className="roi-mode-desc">{isForward ? t('roi.modeForwardDesc') : t('roi.modeBacktestDesc')}</p>

      {!result && <GrowthFunnelStrip source="roi" />}

      <form className="roi-form" onSubmit={onSubmit}>
        <label className="roi-field">
          <span>{t('roi.asset')}</span>
          <select value={symbol} onChange={(e) => onSymbolChange(e.target.value)}>
            {assets.map((a) => (
              <option key={a.symbol} value={a.symbol}>
                {a.name} ({a.symbol})
              </option>
            ))}
          </select>
          {selected && (
            <small className="roi-hint">
              {t('roi.historyFrom', { date: selected.history_from })} · {selected.asset_class} · {selected.region}
            </small>
          )}
        </label>

        <label className="roi-field">
          <span>{isForward ? t('roi.amountToday') : t('roi.amount')}</span>
          <input
            type="number"
            min={100}
            max={100000000}
            step={100}
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value) || 0)}
          />
        </label>

        {isForward ? (
          <>
            <label className="roi-field">
              <span>{t('roi.horizon', { n: years })}</span>
              <input
                type="range"
                min={1}
                max={40}
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
              />
              <div className="roi-year-marks">
                <span>1</span>
                <span>10</span>
                <span>20</span>
                <span>30</span>
                <span>40</span>
              </div>
            </label>
            <label className="roi-field">
              <span>{t('roi.monthly')}</span>
              <input
                type="number"
                min={0}
                max={1000000}
                step={50}
                value={monthly}
                onChange={(e) => setMonthly(Number(e.target.value) || 0)}
              />
            </label>
          </>
        ) : (
          <label className="roi-field">
            <span>{t('roi.start')}</span>
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} min="2000-01-01" />
          </label>
        )}

        <fieldset className="roi-strategies">
          <legend>{t('roi.strategy')}</legend>
          <div className="roi-strategy-grid">
            {STRATEGIES.map((s) => (
              <button
                key={s}
                type="button"
                className={`roi-strategy-btn ${strategy === s ? 'active' : ''}`}
                onClick={() => setStrategy(s)}
              >
                <strong>{t(`roi.strategies.${s}`)}</strong>
                <span>{t(`roi.strategyDesc.${s}`)}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <button type="submit" className="btn tap-target roi-submit" disabled={calculating || amount <= 0 || loadingAssets}>
          {calculating ? t('roi.calculating') : isForward ? t('roi.project') : t('roi.calculate')}
        </button>
        {calculating && <p className="roi-calculating-hint">{t('roi.calculating')}</p>}
      </form>

      {result && (
        <div className="roi-result-banner" role="status">
          <strong>{result.name}</strong>
          <span className={result.roi_pct >= 0 ? 'pos' : 'neg'}>{fmtPct(result.roi_pct)} ROI</span>
          <span>{fmtMoney(result.final_value, dateLocale)} USD</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' })}>
            {t('roi.seeDetails')}
          </button>
        </div>
      )}

      {error && (
        <ErrorState
          message={error}
          onRetry={() => (assetsError ? void loadAssets() : void runCalculate())}
        />
      )}

      {result && (
        <section className="roi-results" ref={resultsRef}>
          <h3 className="roi-results-title">{isForward ? t('roi.project') : t('roi.calculate')} — {result.name}</h3>
          {result.current_cycle && result.sentiment && (
            <div className="roi-live-strip">
              <div className="roi-live-card">
                <span>{t('roi.nowCycle')}</span>
                <strong>{result.current_cycle.phase}</strong>
                <small>{result.current_cycle.rationale}</small>
              </div>
              <div className="roi-live-card">
                <span>{t('roi.nowSentiment')}</span>
                <strong className={`roi-sent-${result.sentiment.label}`}>
                  {t(`roi.sentiment.${result.sentiment.label as 'bullish' | 'constructive' | 'neutral' | 'cautious' | 'bearish'}`)}
                </strong>
                <small>
                  {t('roi.sentimentScore', { n: result.sentiment.score })} · ×{result.sentiment.multiplier}
                </small>
              </div>
              <div className="roi-live-card">
                <span>{t('roi.histCagr')}</span>
                <strong>{fmtPct(result.current_cycle.historical_cagr_pct)}</strong>
                <small>{t('roi.histCagrHint')}</small>
              </div>
            </div>
          )}

          <div className="roi-stats">
            <div className="roi-stat">
              <span>{isForward ? t('roi.valueInYears', { n: result.years }) : t('roi.finalValue')}</span>
              <strong className={result.profit >= 0 ? 'pos' : 'neg'}>{fmtMoney(result.final_value, dateLocale)}</strong>
            </div>
            {result.final_optimistic != null && (
              <div className="roi-stat">
                <span>{t('roi.optimistic')}</span>
                <strong className="pos">{fmtMoney(result.final_optimistic, dateLocale)}</strong>
              </div>
            )}
            {result.final_pessimistic != null && (
              <div className="roi-stat">
                <span>{t('roi.pessimistic')}</span>
                <strong className="neg">{fmtMoney(result.final_pessimistic, dateLocale)}</strong>
              </div>
            )}
            <div className="roi-stat">
              <span>{t('roi.roi')}</span>
              <strong className={result.roi_pct >= 0 ? 'pos' : 'neg'}>{fmtPct(result.roi_pct)}</strong>
            </div>
            <div className="roi-stat">
              <span>{t('roi.cagr')}</span>
              <strong>{fmtPct(result.cagr_pct)}</strong>
            </div>
            {!isForward && (
              <div className="roi-stat">
                <span>{t('roi.maxDd')}</span>
                <strong className="neg">−{result.max_drawdown_pct.toFixed(1)}%</strong>
              </div>
            )}
            <div className="roi-stat">
              <span>{t('roi.cycleSource')}</span>
              <strong className="roi-cycle-src">{result.cycle_source}</strong>
            </div>
          </div>

          {result.buy_hold && (
            <p className="roi-compare">
              {t('roi.compareBh', {
                cycle: fmtPct(result.roi_pct),
                bh: fmtPct(result.buy_hold.roi_pct),
              })}
            </p>
          )}

          <div className="roi-chart-wrap">
            <div className="roi-chart-legend">
              <span className="roi-leg-equity">{isForward ? t('roi.chartBase') : t('roi.chartEquity')}</span>
              {result.optimistic_curve && <span className="roi-leg-opt">{t('roi.chartOpt')}</span>}
              {result.pessimistic_curve && <span className="roi-leg-pes">{t('roi.chartPes')}</span>}
              {result.buy_hold && <span className="roi-leg-bh">{t('roi.chartBh')}</span>}
              {result.price_series?.length > 0 && <span className="roi-leg-price">{t('roi.chartPrice')}</span>}
            </div>
            <RoiEquityChart
              equity={result.equity_curve}
              buyHold={result.buy_hold?.equity_curve}
              optimistic={result.optimistic_curve}
              pessimistic={result.pessimistic_curve}
              price={result.price_series}
            />
          </div>

          <RoiShareCard result={result} />

          {result.milestones && result.milestones.length > 0 && (
            <div className="roi-milestones">
              <h3>{t('roi.milestones')}</h3>
              <div className="roi-milestone-grid">
                {result.milestones
                  .filter((m) => [5, 10, 15, 20, 25, 30, 40].includes(m.year) || m.year === result.years)
                  .map((m) => (
                    <div key={m.year} className="roi-milestone">
                      <span>{t('roi.yearN', { n: m.year })}</span>
                      <strong>{fmtMoney(m.base, dateLocale)}</strong>
                      <small>
                        {fmtMoney(m.pessimistic, dateLocale)} – {fmtMoney(m.optimistic, dateLocale)}
                      </small>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {result.btc_cycle_aths?.length > 0 && (
            <div className="roi-ath-timeline">
              <h3>{t('roi.btcAths')}</h3>
              <ul>
                {result.btc_cycle_aths.map((ath) => (
                  <li key={ath.date}>
                    <span>{ath.label}</span>
                    <span>{ath.date}</span>
                    <strong>${ath.price.toLocaleString(dateLocale)}</strong>
                  </li>
                ))}
              </ul>
              <p className="roi-ath-note">{t('roi.btcAthNote')}</p>
            </div>
          )}

          {result.trades?.length > 0 && (
            <div className="roi-trades">
              <h3>{t('roi.trades')}</h3>
              <ul>
                {result.trades.slice(0, 24).map((tr, i) => (
                  <li key={`${tr.time}-${i}`} className={`roi-trade roi-trade-${tr.action}`}>
                    <span className="roi-trade-action">{tr.action === 'buy' ? t('common.buy') : t('common.sell')}</span>
                    <span>{new Date(tr.time * 1000).toLocaleDateString(dateLocale)}</span>
                    <span>${tr.price.toLocaleString(dateLocale, { maximumFractionDigits: 2 })}</span>
                    <span className="roi-trade-phase">{tr.phase}</span>
                    <span className="roi-trade-note">{tr.rationale}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="roi-meta">
            {isForward
              ? t('roi.metaForward', {
                  from: result.data_start ?? '—',
                  to: result.data_end ?? '—',
                  years: result.years,
                  locale,
                })
              : t('roi.meta', {
                  from: result.data_start ?? '—',
                  to: result.data_end ?? '—',
                  bars: result.bars,
                  locale,
                })}
          </p>
          <div className="roi-result-actions">
            <button
              type="button"
              className="btn btn-ghost tap-target"
              onClick={() => explainWithAgent(result)}
            >
              {t('roi.explainWithAgent')}
            </button>
          </div>
          <p className="roi-disclaimer">{result.disclaimer}</p>
        </section>
      )}

      {result && <GrowthFunnelStrip source="roi" />}
    </div>
  )
}
