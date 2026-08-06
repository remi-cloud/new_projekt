import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { phaseTagClass, confidenceTier } from '../utils/phaseTags'
import { useLazyVisible } from '../hooks/useLazyVisible'
import { useLiveQuote } from '../hooks/useLiveQuote'
import { AssetCycleAssessment } from '../types'
import { ChartPreset, ChartResponse, INTRADAY_CHART_PRESETS, SWING_CHART_PRESETS } from '../types/chart'
import {
  ChartIndicatorFlags,
  ChartIndicatorId,
  CYCLES_CHART_INDICATORS,
  DEFAULT_CHART_INDICATORS,
} from '../utils/chartIndicators'
import { presetToTvInterval } from '../utils/tradingViewSymbol'
import { TradePanel } from './PaperTrading'
import { QuickTradeButtons } from './QuickTradeButtons'
import { ChartLoader } from './TradingChart'
import { PriceHeader } from './PriceHeader'
import { TradingViewChart, TradingViewQuote } from './TradingViewChart'
import { TagTip } from './TagTip'
import { AskAgentButton } from './AskAgentButton'
import { CommunityActions } from './CommunityActions'
import { InstrumentShareMenu } from './InstrumentShareMenu'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import type { TranslationPath } from '../i18n'

const INDICATOR_TOGGLES: { id: ChartIndicatorId; labelKey: TranslationPath }[] = [
  { id: 'volume', labelKey: 'chart.indVolume' },
  { id: 'sma', labelKey: 'chart.indSma' },
  { id: 'ema', labelKey: 'chart.indEma' },
  { id: 'bb', labelKey: 'chart.indBb' },
  { id: 'rsi', labelKey: 'chart.indRsi' },
  { id: 'macd', labelKey: 'chart.indMacd' },
  { id: 'atr', labelKey: 'chart.indAtr' },
]

interface InstrumentPanelProps {
  item: AssetCycleAssessment
  expanded?: boolean
}

type ChartMode = 'price' | 'cycles' | 'tv'

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
  const { t } = useLocale()
  const { asset, region, signal, phase } = useDomainLabels()
  const { ref, visible } = useLazyVisible()
  const [chartData, setChartData] = useState<ChartResponse | null>(null)
  const [preset, setPreset] = useState<ChartPreset>('1D')
  const [chartMode, setChartMode] = useState<ChartMode>('price')
  const [indicators, setIndicators] = useState<Required<ChartIndicatorFlags>>(DEFAULT_CHART_INDICATORS)
  const [tradesRevision, setTradesRevision] = useState(0)
  const [openTip, setOpenTip] = useState<string | null>(null)

  useEffect(() => {
    setIndicators(chartMode === 'cycles' ? { ...CYCLES_CHART_INDICATORS } : { ...DEFAULT_CHART_INDICATORS })
  }, [chartMode])

  const toggleIndicator = (id: ChartIndicatorId) => {
    setIndicators((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const detailHref = `/instrument/${encodeURIComponent(item.symbol)}`

  const liveQuote = useLiveQuote(
    item.symbol,
    (visible || expanded) && chartMode !== 'tv',
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

  const priceBlock =
    expanded && chartMode === 'tv' ? (
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
    )

  return (
    <article
      className={`instrument-panel terminal-panel card-stretch-host ${expanded ? 'expanded' : ''}`}
      ref={ref}
    >
      {!expanded && (
        <Link
          to={detailHref}
          className="card-stretch-link"
          aria-label={`${item.name} ${item.symbol}`}
        />
      )}

      {priceBlock}

      {expanded ? (
        <div className="instrument-chart-wrap terminal-frame">
          <div className="terminal-chrome">
            <div className="terminal-chrome-left">
              <span className="terminal-chrome-symbol">{item.symbol}</span>
              <span className="terminal-chrome-name">{item.name}</span>
            </div>
            <span className="terminal-chrome-live">{t('common.live')}</span>
          </div>

          <div className="chart-mode-tabs">
            <button
              type="button"
              className={`tf-btn ${chartMode === 'price' ? 'active' : ''}`}
              onClick={() => setChartMode('price')}
            >
              {t('chart.priceChart')}
            </button>
            <button
              type="button"
              className={`tf-btn ${chartMode === 'cycles' ? 'active' : ''}`}
              onClick={() => setChartMode('cycles')}
            >
              {t('chart.cyclesRsi')}
            </button>
            <button
              type="button"
              className={`tf-btn ${chartMode === 'tv' ? 'active' : ''}`}
              onClick={() => setChartMode('tv')}
            >
              {t('chart.liveTv')}
            </button>
          </div>

          {chartMode !== 'tv' && (
            <>
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
              <div className="chart-indicator-toggles" role="group" aria-label={t('chart.indicators')}>
                {INDICATOR_TOGGLES.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`tf-btn chart-ind-btn ${indicators[item.id] ? 'active' : ''}`}
                    onClick={() => toggleIndicator(item.id)}
                    aria-pressed={indicators[item.id]}
                  >
                    {t(item.labelKey)}
                  </button>
                ))}
              </div>
            </>
          )}

          {chartMode === 'tv' ? (
            <TradingViewChart
              symbol={item.symbol}
              assetClass={item.asset_class}
              region={item.region}
              height={400}
              interval={presetToTvInterval(preset)}
            />
          ) : (
            <ChartLoader
              symbol={item.symbol}
              preset={preset}
              height={420}
              mode="candle"
              enabled
              onData={setChartData}
              tradesRevision={tradesRevision}
              showRsiShadow={indicators.rsi}
              indicators={indicators}
              onPresetChange={setPreset}
            />
          )}
          {chartMode !== 'tv' && (
            <div className="chart-trade-legend">
              {indicators.rsi && <span className="legend-rsi">{t('chart.legendRsi')}</span>}
              {indicators.sma && <span className="legend-sma">{t('chart.legendSma')}</span>}
              {indicators.ema && <span className="legend-ema">{t('chart.legendEma')}</span>}
              {indicators.bb && <span className="legend-bb">{t('chart.legendBb')}</span>}
              {indicators.volume && <span className="legend-vol">{t('chart.legendVolume')}</span>}
              {indicators.macd && <span className="legend-macd">{t('chart.legendMacd')}</span>}
              {indicators.atr && <span className="legend-atr">{t('chart.legendAtr')}</span>}
              {chartMode === 'cycles' && (
                <>
                  <span className="legend-cycle-buy">{t('chart.legendCycleBuy')}</span>
                  <span className="legend-cycle-short">{t('chart.legendCycleShort')}</span>
                  <span className="legend-cycle-sell">{t('chart.legendCycleSell')}</span>
                </>
              )}
              <span className="legend-buy">{t('chart.legendPaperBuy')}</span>
              <span className="legend-sell">{t('chart.legendPaperSell')}</span>
              <span className="legend-open">{t('chart.legendOpen')}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="instrument-chart-wrap terminal-frame instrument-chart-preview">
          {visible ? (
            <ChartLoader
              symbol={item.symbol}
              preset="3M"
              height={150}
              mode="area"
              enabled={visible}
              onData={setChartData}
              tradesRevision={tradesRevision}
              showRsiShadow={false}
            />
          ) : (
            <div className="chart-placeholder" style={{ height: 150 }} />
          )}
        </div>
      )}

      <div className={`instrument-footer${expanded ? '' : ' card-stretch-above'}`}>
        <div className="instrument-share-row">
          <AskAgentButton mode="instrument" symbol={item.symbol} name={item.name} compact />
          <CommunityActions
            symbol={item.symbol}
            name={item.name}
            community={item.community}
            compact
          />
          <InstrumentShareMenu
            symbol={item.symbol}
            name={item.name}
            kind="instrument"
            signal={signal[item.signal]}
            compact
          />
        </div>
        <p className="tag-tips-hint">{t('tagTips.clickHint')}</p>
        <div className="market-tags">
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
          {item.chain && (
            <TagTip
              tipId="chain"
              openId={openTip}
              onOpen={setOpenTip}
              className="chain"
              label={item.chain}
              title={item.chain}
              body={t('tagTips.chain.body', { chain: item.chain })}
              hint={t('tagTips.chain.hint')}
            />
          )}
          {(item.related_symbols ?? []).slice(0, 3).map((rel) => (
            <TagTip
              key={rel}
              tipId={`rel-${rel}`}
              openId={openTip}
              onOpen={setOpenTip}
              className="related"
              label={rel.replace('-USD', '')}
              title={rel}
              body={t('tagTips.related.body', { symbol: rel })}
              hint={t('tagTips.related.hint')}
            />
          ))}
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
          {item.seasonality?.available && item.seasonality.avg_pct != null ? (
            <TagTip
              tipId="season"
              openId={openTip}
              onOpen={setOpenTip}
              className={item.seasonality.bias === 'down' ? 'season-down' : 'season-up'}
              label={
                item.seasonality.bias === 'down'
                  ? t('instrument.seasonalityDown', { pct: item.seasonality.avg_pct.toFixed(1) })
                  : t('instrument.seasonalityUp', { pct: item.seasonality.avg_pct.toFixed(1) })
              }
              title={t('instrument.seasonalityTip')}
              body={`${item.seasonality.source ?? ''} · ${item.seasonality.calendar_season ?? ''}`}
              hint={t('instrument.seasonalityTip')}
            />
          ) : (
            <TagTip
              tipId="season"
              openId={openTip}
              onOpen={setOpenTip}
              className="season-na"
              label={t('instrument.seasonalityNa')}
              title={t('instrument.seasonalityTip')}
              body={item.seasonality?.reason || t('instrument.seasonalityTip')}
              hint={t('instrument.seasonalityTip')}
            />
          )}
        </div>

        {rationaleChunks.length > 0 && (
          <div className="market-rationale-tips">
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
        <QuickTradeButtons
          symbol={item.symbol}
          compact={!expanded}
          onTrade={() => setTradesRevision((n) => n + 1)}
        />
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
