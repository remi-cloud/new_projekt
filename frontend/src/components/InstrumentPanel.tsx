import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ASSET_LABELS, PHASE_LABELS, REGION_LABELS, SIGNAL_LABELS } from '../constants'
import { useLazyVisible } from '../hooks/useLazyVisible'
import { AssetCycleAssessment } from '../types'
import { ChartPreset, ChartResponse, INTRADAY_CHART_PRESETS, SWING_CHART_PRESETS } from '../types/chart'
import { TradePanel } from './PaperTrading'
import { ChartLoader } from './TradingChart'
import { PriceHeader } from './PriceHeader'

interface InstrumentPanelProps {
  item: AssetCycleAssessment
  expanded?: boolean
}

export function InstrumentPanel({ item, expanded = false }: InstrumentPanelProps) {
  const navigate = useNavigate()
  const { ref, visible } = useLazyVisible()
  const [chartData, setChartData] = useState<ChartResponse | null>(null)
  const [preset, setPreset] = useState<ChartPreset>('3M')

  const openDetail = () => navigate(`/instrument/${encodeURIComponent(item.symbol)}`)

  return (
    <article
      className={`instrument-panel ${expanded ? 'expanded' : ''}`}
      ref={ref}
      onClick={expanded ? undefined : openDetail}
      role={expanded ? undefined : 'button'}
      tabIndex={expanded ? undefined : 0}
      onKeyDown={expanded ? undefined : (e) => e.key === 'Enter' && openDetail()}
    >
      <PriceHeader
        name={item.name}
        symbol={item.symbol}
        assetClass={item.asset_class}
        chart={chartData}
        fallbackPrice={item.price}
        change24h={item.change_pct_24h}
        change7d={item.change_pct_7d}
        signalLabel={SIGNAL_LABELS[item.signal]}
        signalAction={item.signal}
        compact={!expanded}
      />

      <div className="instrument-chart-wrap" onClick={(e) => expanded && e.stopPropagation()}>
        {expanded && (
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
          <ChartLoader
            symbol={item.symbol}
            preset={expanded ? preset : '3M'}
            height={expanded ? 260 : 120}
            mode={expanded ? 'candle' : 'area'}
            enabled={visible || expanded}
            onData={setChartData}
          />
        )}
        {!visible && !expanded && <div className="chart-placeholder" style={{ height: 120 }} />}
      </div>

      <div className="instrument-footer">
        <div className="market-tags">
          <span className={`tag ${item.asset_class}`}>{ASSET_LABELS[item.asset_class]}</span>
          <span className="tag region">{REGION_LABELS[item.region as keyof typeof REGION_LABELS] ?? item.region}</span>
          <span className="tag">{PHASE_LABELS[item.price_phase] ?? item.price_phase}</span>
          <span className={`signal-tag signal-${item.signal}`}>{item.confidence}%</span>
        </div>
        {!expanded && (
          <span className="tap-hint">Stuknij aby powiększyć →</span>
        )}
        {expanded && (
          <TradePanel symbol={item.symbol} name={item.name} price={item.price} />
        )}
        <p className="market-rationale">{item.rationale}</p>
      </div>
    </article>
  )
}
