import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ASSET_LABELS, PHASE_LABELS, REGION_LABELS, SIGNAL_LABELS } from '../constants'
import { phaseTagClass, confidenceTier } from '../utils/phaseTags'
import { useLazyVisible } from '../hooks/useLazyVisible'
import { useLiveQuote } from '../hooks/useLiveQuote'
import { AssetCycleAssessment } from '../types'
import { ChartPreset, ChartResponse, INTRADAY_CHART_PRESETS, SWING_CHART_PRESETS } from '../types/chart'
import { presetToTvInterval } from '../utils/tradingViewSymbol'
import { TradePanel } from './PaperTrading'
import { ChartLoader } from './TradingChart'
import { PriceHeader } from './PriceHeader'
import { TradingViewChart, TradingViewQuote } from './TradingViewChart'

interface InstrumentPanelProps {
  item: AssetCycleAssessment
  expanded?: boolean
}

type ChartMode = 'live' | 'cycles'

export function InstrumentPanel({ item, expanded = false }: InstrumentPanelProps) {
  const navigate = useNavigate()
  const { ref, visible } = useLazyVisible()
  const [chartData, setChartData] = useState<ChartResponse | null>(null)
  const [preset, setPreset] = useState<ChartPreset>('1m')
  const [chartMode, setChartMode] = useState<ChartMode>('live')
  const [tradesRevision, setTradesRevision] = useState(0)

  const openDetail = () => navigate(`/instrument/${encodeURIComponent(item.symbol)}`)

  const liveQuote = useLiveQuote(
    item.symbol,
    (visible || expanded) && chartMode === 'cycles',
    expanded ? 15_000 : 60_000,
  )
  const displayPrice = liveQuote?.price ?? chartData?.current_price ?? item.price

  return (
    <article
      className={`instrument-panel terminal-panel ${expanded ? 'expanded' : ''}`}
      ref={ref}
      onClick={expanded ? undefined : openDetail}
      role={expanded ? undefined : 'button'}
      tabIndex={expanded ? undefined : 0}
      onKeyDown={expanded ? undefined : (e) => e.key === 'Enter' && openDetail()}
    >
      {expanded && chartMode === 'live' ? (
        <div className="price-header expanded">
          <div className="price-header-top">
            <div className="price-header-symbol">
              <span className="price-ticker">{item.symbol}</span>
              <span className="price-name">{item.name}</span>
            </div>
            <span className={`signal-tag signal-${item.signal}`}>{SIGNAL_LABELS[item.signal]}</span>
          </div>
          <TradingViewQuote symbol={item.symbol} assetClass={item.asset_class} region={item.region} />
          <p className="tv-price-hint">Cena live · TradingView (sesja + after-hours)</p>
        </div>
      ) : (
        <PriceHeader
          name={item.name}
          symbol={item.symbol}
          assetClass={item.asset_class}
          chart={chartData}
          fallbackPrice={item.price}
          livePrice={displayPrice}
          change24h={liveQuote?.change_pct_24h ?? item.change_pct_24h}
          change7d={item.change_pct_7d}
          signalLabel={SIGNAL_LABELS[item.signal]}
          signalAction={item.signal}
          compact={!expanded}
        />
      )}

      <div className="instrument-chart-wrap terminal-frame" onClick={(e) => expanded && e.stopPropagation()}>
        {expanded && (
          <div className="terminal-chrome">
            <div className="terminal-chrome-left">
              <span className="terminal-chrome-symbol">{item.symbol}</span>
              <span className="terminal-chrome-name">{item.name}</span>
            </div>
            <span className="terminal-chrome-live">LIVE</span>
          </div>
        )}

        {expanded && (
          <div className="chart-mode-tabs">
            <button
              type="button"
              className={`tf-btn ${chartMode === 'live' ? 'active' : ''}`}
              onClick={() => setChartMode('live')}
            >
              Live · TradingView
            </button>
            <button
              type="button"
              className={`tf-btn ${chartMode === 'cycles' ? 'active' : ''}`}
              onClick={() => setChartMode('cycles')}
            >
              Cykle · RSI · WEJ/WYJ
            </button>
          </div>
        )}

        {expanded && chartMode === 'cycles' && (
          <div className="chart-timeframes">
            <div className="chart-tf-row">
              {INTRADAY_CHART_PRESETS.map((p) => (
                <button
                  key={p}
                  type="button"
                  className={`tf-btn tf-intraday ${preset === p ? 'active' : ''}`}
                  onClick={() => setPreset(p)}
                >
                  {p}
                </button>
              ))}
            </div>
            <div className="chart-tf-row">
              {SWING_CHART_PRESETS.map((p) => (
                <button
                  key={p}
                  type="button"
                  className={`tf-btn ${preset === p ? 'active' : ''}`}
                  onClick={() => setPreset(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {(visible || expanded) && (
          <>
            {expanded && chartMode === 'live' ? (
              <>
                <div className="chart-timeframes chart-tv-intervals">
                  <div className="chart-tf-row">
                    {(['1m', '5m', '15m', '1H', '4H', '1D', '1W'] as ChartPreset[]).map((p) => (
                      <button
                        key={p}
                        type="button"
                        className={`tf-btn tf-intraday ${preset === p ? 'active' : ''}`}
                        onClick={() => setPreset(p)}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
                <TradingViewChart
                  symbol={item.symbol}
                  assetClass={item.asset_class}
                  region={item.region}
                  height={400}
                  interval={presetToTvInterval(preset)}
                />
              </>
            ) : (
              <ChartLoader
                symbol={item.symbol}
                preset={expanded ? preset : '3M'}
                height={expanded ? 360 : 150}
                mode={expanded ? 'candle' : 'area'}
                enabled={visible || expanded}
                onData={setChartData}
                tradesRevision={tradesRevision}
                showRsiShadow={expanded && chartMode === 'cycles'}
              />
            )}
            {expanded && chartMode === 'cycles' && (
              <div className="chart-trade-legend">
                <span className="legend-rsi">RSI zielone wyprzedanie / czerwone wykupienie</span>
                <span className="legend-cycle-buy">▲ WEJ — wejście cykliczne</span>
                <span className="legend-cycle-sell">▼ WYJ — wyjście cykliczne</span>
                <span className="legend-buy">▲ Paper kupno</span>
                <span className="legend-sell">▼ Paper sprzedaż</span>
                <span className="legend-open">● Otwarcie pozycji</span>
              </div>
            )}
          </>
        )}
        {!visible && !expanded && <div className="chart-placeholder" style={{ height: 150 }} />}
      </div>

      <div className="instrument-footer">
        <div className="market-tags">
          <span className={`tag ${item.asset_class}`}>{ASSET_LABELS[item.asset_class]}</span>
          <span className="tag region">{REGION_LABELS[item.region as keyof typeof REGION_LABELS] ?? item.region}</span>
          <span className={`tag phase-tag ${phaseTagClass(item.price_phase)}`}>
            {PHASE_LABELS[item.price_phase] ?? item.price_phase}
          </span>
          {item.momentum_score != null && (
            <span
              className={`tag momentum-score phase-tag ${phaseTagClass(item.momentum_phase)} ${item.is_momentum_pick ? 'momentum-pick' : ''}`}
            >
              Mom. {item.momentum_score.toFixed(0)}
              {item.momentum_phase ? ` · ${PHASE_LABELS[item.momentum_phase] ?? item.momentum_phase}` : ''}
            </span>
          )}
          {item.is_momentum_pick && <span className="tag momentum-pick">⚡ Momentum + cykl</span>}
          <span
            className={`signal-tag signal-${item.signal} conf-tier-${confidenceTier(item.confidence)}`}
            title={`Pewność sygnału ${item.confidence}% — im wyżej, tym silniejsza okazja ${item.signal === 'buy' ? 'kupna' : item.signal === 'sell' ? 'sprzedaży' : ''}`}
          >
            {item.confidence}%
          </span>
        </div>
        {!expanded && (
          <span className="tap-hint">Stuknij aby powiększyć →</span>
        )}
        {expanded && (
          <TradePanel
            symbol={item.symbol}
            name={item.name}
            price={displayPrice}
            onTrade={() => setTradesRevision((n) => n + 1)}
          />
        )}
        <p className="market-rationale">{item.rationale}</p>
      </div>
    </article>
  )
}
