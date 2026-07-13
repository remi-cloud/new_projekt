import { MarketSummary } from '../types'

export function MarketSummaryBanner({ summary }: { summary: MarketSummary }) {
  const outlookClass = summary.outlook === 'bullish' ? 'bullish' : summary.outlook === 'bearish' ? 'bearish' : 'mixed'
  return (
    <div className={`market-summary ${outlookClass}`}>
      <div className="market-summary-title">Ocena globalna · {summary.total_assets} instrumentów</div>
      <div className="market-summary-text">{summary.outlook_label}</div>
      <div className="market-summary-stats">
        <span>Kupuj: {summary.by_signal.buy ?? 0}</span>
        <span>Obserwuj: {summary.by_signal.watch ?? 0}</span>
        <span>Trzymaj: {summary.by_signal.hold ?? 0}</span>
        <span>Sprzedaj: {summary.by_signal.sell ?? 0}</span>
      </div>
    </div>
  )
}

export { InstrumentPanel } from './InstrumentPanel'
