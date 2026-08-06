import { MarketSummary } from '../types'
import { useLocale } from '../context/LocaleContext'

export function MarketSummaryBanner({ summary }: { summary: MarketSummary }) {
  const { t } = useLocale()
  const outlookClass = summary.outlook === 'bullish' ? 'bullish' : summary.outlook === 'bearish' ? 'bearish' : 'mixed'
  const outlookText =
    summary.outlook === 'bullish'
      ? t('banner.outlookBullish')
      : summary.outlook === 'bearish'
        ? t('banner.outlookBearish')
        : t('banner.outlookMixed')

  return (
    <div className={`market-summary ${outlookClass}`}>
      <div className="market-summary-title">{t('banner.globalAssessment', { n: summary.total_assets })}</div>
      <div className="market-summary-text">{outlookText}</div>
      <div className="market-summary-stats">
        <span>{t('banner.buyCount', { n: summary.by_signal.buy ?? 0 })}</span>
        <span>{t('banner.watchCount', { n: summary.by_signal.watch ?? 0 })}</span>
        <span>{t('banner.holdCount', { n: summary.by_signal.hold ?? 0 })}</span>
        <span>{t('banner.sellCount', { n: summary.by_signal.sell ?? 0 })}</span>
      </div>
    </div>
  )
}

export { InstrumentPanel } from './InstrumentPanel'
