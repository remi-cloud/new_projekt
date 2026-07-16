import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
import { TagTip } from './TagTip'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import type { TranslationPath } from '../i18n'

interface InstrumentPanelProps {
  item: AssetCycleAssessment
  expanded?: boolean
}

type ChartMode = 'live' | 'cycles'

type RationaleKind = 'cycle' | 'price' | 'momentum' | 'other'

function parseRationaleChunks(raw: string): { kind: RationaleKind; label: string; detail: string; full: string }[] {
  const matches = [...raw.matchAll(/\[([^\]]+)\]/g)].map((m) => m[1].trim())
  const parts = matches.length > 0 ? matches : raw.trim() ? [raw.trim()] : []
  return parts.map((full) => {
    const idx = full.indexOf(':')
    const label = (idx >= 0 ? full.slice(0, idx) : full).trim()
    const detail = (idx >= 0 ? full.slice(idx + 1) : full).trim()
    const low = label.toLowerCase()
    let kind: RationaleKind = 'other'
    if (low.includes('cykl') || low.includes('cycle') || low.includes('btc') || low.includes('pres')) kind = 'cycle'
    else if (low.includes('cena') || low.includes('price') || low.includes('prix') || low.includes('preis')) kind = 'price'
    else if (low.includes('momentum') || low.includes('mom.')) kind = 'momentum'
    return { kind, label, detail, full }
  })
}

export function InstrumentPanel({ item, expanded = false }: InstrumentPanelProps) {
  const navigate = useNavigate()
  const { t } = useLocale()
  const { asset, region, signal, phase } = useDomainLabels()
  const { ref, visible } = useLazyVisible()
  const [chartData, setChartData] = useState<ChartResponse | null>(null)
  const [preset, setPreset] = useState<ChartPreset>('1m')
  const [chartMode, setChartMode] = useState<ChartMode>('live')
  const [tradesRevision, setTradesRevision] = useState(0)
  const [openTip, setOpenTip] = useState<string | null>(null)

  const openDetail = () => navigate(`/instrument/${encodeURIComponent(item.symbol)}`)

  const liveQuote = useLiveQuote(
    item.symbol,
    (visible || expanded) && chartMode === 'cycles',
    expanded ? 15_000 : 60_000,
  )
  const displayPrice = liveQuote?.price ?? chartData?.current_price ?? item.price
  const confTier = confidenceTier(item.confidence)
  const regionKey = (['global', 'us', 'eu', 'asia', 'em', 'pl'] as const).includes(
    item.region as 'global' | 'us' | 'eu' | 'asia' | 'em' | 'pl',
  )
    ? (item.region as 'global' | 'us' | 'eu' | 'asia' | 'em' | 'pl')
    : 'global'
  const phaseKey = item.price_phase || 'neutral'
  const momPhaseKey = item.momentum_phase || ''

  const rationaleChunks = useMemo(() => parseRationaleChunks(item.rationale || ''), [item.rationale])

  const tipForKind = (kind: RationaleKind) => {
    if (kind === 'cycle') {
      return { body: t('tagTips.layerCycle.body'), hint: t('tagTips.layerCycle.hint') }
    }
    if (kind === 'price') {
      return { body: t('tagTips.layerPrice.body'), hint: t('tagTips.layerPrice.hint') }
    }
    if (kind === 'momentum') {
      return { body: t('tagTips.layerMomentum.body'), hint: t('tagTips.layerMomentum.hint') }
    }
    return { body: t('tagTips.layerOther.body'), hint: t('tagTips.layerOther.hint') }
  }

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
            <span className={`signal-tag signal-${item.signal}`}>{signal[item.signal]}</span>
          </div>
          <TradingViewQuote symbol={item.symbol} assetClass={item.asset_class} region={item.region} />
          <p className="tv-price-hint">{t('chart.livePriceHint')}</p>
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
          signalLabel={signal[item.signal]}
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
            <span className="terminal-chrome-live">{t('common.live')}</span>
          </div>
        )}

        {expanded && (
          <div className="chart-mode-tabs">
            <button
              type="button"
              className={`tf-btn ${chartMode === 'live' ? 'active' : ''}`}
              onClick={() => setChartMode('live')}
            >
              {t('chart.liveTv')}
            </button>
            <button
              type="button"
              className={`tf-btn ${chartMode === 'cycles' ? 'active' : ''}`}
              onClick={() => setChartMode('cycles')}
            >
              {t('chart.cyclesRsi')}
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
                <span className="legend-rsi">{t('chart.legendRsi')}</span>
                <span className="legend-cycle-buy">{t('chart.legendCycleBuy')}</span>
                <span className="legend-cycle-sell">{t('chart.legendCycleSell')}</span>
                <span className="legend-buy">{t('chart.legendPaperBuy')}</span>
                <span className="legend-sell">{t('chart.legendPaperSell')}</span>
                <span className="legend-open">{t('chart.legendOpen')}</span>
              </div>
            )}
          </>
        )}
        {!visible && !expanded && <div className="chart-placeholder" style={{ height: 150 }} />}
      </div>

      <div className="instrument-footer">
        <p className="tag-tips-hint">{t('tagTips.clickHint')}</p>
        <div className="market-tags" onClick={(e) => e.stopPropagation()}>
          <TagTip
            tipId="asset"
            openId={openTip}
            onOpen={setOpenTip}
            className={item.asset_class}
            label={asset[item.asset_class]}
            title={asset[item.asset_class]}
            body={t(`tagTips.asset.${item.asset_class}.body` as TranslationPath)}
            hint={t(`tagTips.asset.${item.asset_class}.hint` as TranslationPath)}
          />
          <TagTip
            tipId="region"
            openId={openTip}
            onOpen={setOpenTip}
            className="region"
            label={region[regionKey] ?? item.region}
            title={region[regionKey] ?? item.region}
            body={t(`tagTips.region.${regionKey}.body`)}
            hint={t(`tagTips.region.${regionKey}.hint`)}
          />
          <TagTip
            tipId="phase"
            openId={openTip}
            onOpen={setOpenTip}
            className={`phase-tag ${phaseTagClass(item.price_phase)}`}
            label={phase(item.price_phase)}
            title={phase(item.price_phase)}
            body={t(`tagTips.phase.${phaseKey}.body` as TranslationPath)}
            hint={t(`tagTips.phase.${phaseKey}.hint` as TranslationPath)}
          />
          {item.momentum_score != null && (
            <TagTip
              tipId="momScore"
              openId={openTip}
              onOpen={setOpenTip}
              className="momentum-score"
              label={t('opportunities.momScore', { n: item.momentum_score.toFixed(0) })}
              title={t('opportunities.momScore', { n: item.momentum_score.toFixed(0) })}
              body={t('tagTips.momScore.body', { n: item.momentum_score.toFixed(0) })}
              hint={t('tagTips.momScore.hint')}
            />
          )}
          {momPhaseKey ? (
            <TagTip
              tipId="momPhase"
              openId={openTip}
              onOpen={setOpenTip}
              className={`phase-tag ${phaseTagClass(item.momentum_phase)}`}
              label={phase(momPhaseKey)}
              title={phase(momPhaseKey)}
              body={t(`tagTips.phase.${momPhaseKey}.body` as TranslationPath)}
              hint={t(`tagTips.phase.${momPhaseKey}.hint` as TranslationPath)}
            />
          ) : null}
          {item.is_momentum_pick && (
            <TagTip
              tipId="momPick"
              openId={openTip}
              onOpen={setOpenTip}
              className="momentum-pick"
              label={t('instrument.momentumTag')}
              title={t('instrument.momentumTag')}
              body={t('tagTips.momPick.body')}
              hint={t('tagTips.momPick.hint')}
            />
          )}
          <TagTip
            tipId="conf"
            openId={openTip}
            onOpen={setOpenTip}
            className={`signal-tag signal-${item.signal} conf-tier-${confTier}`}
            label={`${item.confidence}%`}
            title={`${item.confidence}%`}
            body={t(`tagTips.confidence.${confTier}.body`, { n: item.confidence })}
            hint={t(`tagTips.confidence.${confTier}.hint`)}
          />
        </div>

        {rationaleChunks.length > 0 && (
          <div className="market-rationale-tips" onClick={(e) => e.stopPropagation()}>
            {rationaleChunks.map((chunk, i) => {
              const layer = tipForKind(chunk.kind)
              return (
                <TagTip
                  key={`${chunk.label}-${i}`}
                  tipId={`rat-${i}`}
                  openId={openTip}
                  onOpen={setOpenTip}
                  className={`rationale-chip kind-${chunk.kind}`}
                  label={chunk.full}
                  title={chunk.label}
                  body={`${layer.body} ${chunk.detail}`}
                  hint={layer.hint}
                />
              )
            })}
          </div>
        )}

        {!expanded && <span className="tap-hint">{t('instrument.tapExpand')}</span>}
        {expanded && (
          <TradePanel
            symbol={item.symbol}
            name={item.name}
            price={displayPrice}
            onTrade={() => setTradesRevision((n) => n + 1)}
          />
        )}
      </div>
    </article>
  )
}
