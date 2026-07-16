export type AssetClass = 'crypto' | 'stock' | 'etf' | 'index' | 'bond' | 'commodity' | 'forex'
export type SignalAction = 'buy' | 'sell' | 'hold' | 'watch'
export type CyclePhase = 'bear' | 'accumulation' | 'bull' | 'distribution' | 'neutral'
export type Region = 'global' | 'us' | 'eu' | 'asia' | 'em' | 'pl'

export interface BitcoinCycleStatus {
  last_ath_date: string
  last_ath_price: number
  current_price: number
  days_since_ath: number
  bear_phase_end_day: number
  bull_phase_end_day: number
  phase: CyclePhase
  phase_progress_pct: number
  days_remaining_in_phase: number
  signal: SignalAction
  rationale: string
}

export interface PresidentialYearReturn {
  year: string
  year_number: number
  label: string
  avg_return_pct: number
  vs_cycle_avg_pct: number
  bias: string
  tone: 'weak' | 'moderate' | 'strong' | 'best'
  is_current: boolean
}

export interface PresidentialCycleStatus {
  term_start: string
  term_end: string
  president: string
  current_year: string
  year_number: number
  days_into_year: number
  days_remaining_in_year: number
  year_progress_pct: number
  historical_bias: string
  signal: SignalAction
  rationale: string
  benchmark?: string
  benchmark_note?: string
  cycle_avg_return_pct?: number
  year_returns?: PresidentialYearReturn[]
  current_year_expected_return_pct?: number
}

export interface AssetQuote {
  symbol: string
  name: string
  asset_class: AssetClass
  price: number
  change_pct_24h: number | null
  change_pct_7d: number | null
  currency: string
  updated_at: string
}

export interface LiveQuote {
  symbol: string
  price: number
  currency: string
  change_pct_24h: number | null
  updated_at: string | null
}

export interface AssetCycleAssessment {
  symbol: string
  name: string
  asset_class: AssetClass
  region: Region
  price: number
  change_pct_24h: number | null
  change_pct_7d: number | null
  high_52w: number | null
  drawdown_from_high_pct: number | null
  macro_cycle: string
  macro_phase: string
  price_phase: string
  momentum_score: number | null
  momentum_signal: SignalAction | null
  momentum_phase: string | null
  is_momentum_pick: boolean
  signal: SignalAction
  confidence: number
  rationale: string
  updated_at: string
  broker_info?: BrokerPurchaseInfo | null
}

export interface BrokerOption {
  id: string
  name: string
  regions: string[]
  url: string
  notes: string
}

export interface BrokerPurchaseInfo {
  primary_exchange?: string | null
  brokers: BrokerOption[]
  disclaimer: string
}

export interface PearlFind {
  id?: number | null
  agent_id: string
  symbol: string
  name: string
  asset_class: AssetClass
  region: string
  price: number
  change_pct_24h?: number | null
  score: number
  confidence: number
  action: SignalAction
  rationale: string
  source: string
  found_at: string
  broker_info?: BrokerPurchaseInfo | null
}

export interface PearlHunterStatus {
  enabled: boolean
  agents: Array<{
    id: string
    name: string
    last_run_at?: string | null
    last_count?: number
    last_error?: string
  }>
  finds_count: number
  last_run_at?: string | null
}

export interface MarketSummary {
  total_assets: number
  by_signal: Record<string, number>
  by_class: Record<string, number>
  by_region: Record<string, number>
  avg_confidence: number
  outlook: string
  outlook_label: string
}

export interface Opportunity {
  symbol: string
  name: string
  asset_class: AssetClass
  action: SignalAction
  confidence: number
  cycle_source: string
  phase: string
  price: number
  momentum_score: number | null
  momentum_signal: SignalAction | null
  is_momentum_pick: boolean
  rationale: string
  created_at: string
}

export interface RegionalCycleSnapshot {
  region: string
  region_label: string
  cycle_id: string
  phase: string
  signal: SignalAction
  buy_weight: number
  bias: string
  rationale: string
}

export type MacroNewsCategory = 'fed' | 'usa' | 'macro' | 'global' | 'musk'

export interface MacroNewsItem {
  id: string
  title: string
  summary: string | null
  url: string | null
  image_url: string | null
  source_image_url?: string | null
  source: string
  category: MacroNewsCategory
  impact: string
  published_at: string
  is_curated: boolean
  age_minutes?: number | null
}

export interface MacroCalendarEvent {
  id: string
  title: string
  event_date: string
  days_until: number
  category: string
  impact: string
  time_utc: string
  region: string
}

export interface MacroCalendarMonth {
  year: number
  month: number
  events: MacroCalendarEvent[]
  news: MacroNewsItem[]
  fetched_at: string
  poll_interval_seconds: number
}

export interface MacroNewsFeed {
  items: MacroNewsItem[]
  calendar_events: MacroCalendarEvent[]
  fetched_at: string
  counts: Record<string, number>
  sources_count: number
  poll_interval_seconds: number
  fresh_count_1h: number
}

export interface DashboardResponse {
  bitcoin_cycle: BitcoinCycleStatus
  presidential_cycle: PresidentialCycleStatus
  regional_cycles: RegionalCycleSnapshot[]
  opportunities: Opportunity[]
  monitored_assets: AssetQuote[]
  market_assessments: AssetCycleAssessment[]
  market_summary: MarketSummary
  last_scan_at: string | null
  last_price_tick_at: string | null
  live_mode: boolean
  scanner_running: boolean
  scan_in_progress?: boolean
}

export interface AlertSettings {
  phone: string
  sms_enabled: boolean
  push_enabled: boolean
  ntfy_enabled: boolean
  ntfy_topic: string
  min_confidence: number
  alert_on_signal_change: boolean
  alert_on_new_opportunity: boolean
  alert_on_macro_news: boolean
}

export interface NotificationStatus {
  push_configured: boolean
  sms_configured: boolean
  ntfy_configured: boolean
  ntfy_subscribe_url: string
  ntfy_app_url: string
  vapid_public_key: string
  push_subscriptions: number
  settings: AlertSettings
}

export interface TwilioConfig {
  account_sid: string
  auth_token: string
  from_number: string
}

export interface PaperOrderRequest {
  symbol: string
  side: 'buy' | 'sell'
  quantity?: number
  amount_pln?: number
  order_type?: 'market' | 'limit' | 'stop' | 'take_profit'
  limit_price_native?: number
}

export interface PaperLimitOrder {
  id: number
  symbol: string
  name: string
  asset_class: AssetClass
  side: 'buy' | 'sell'
  order_type: 'limit' | 'stop' | 'take_profit'
  limit_price_native: number
  limit_price_pln: number
  amount_pln: number
  quantity_est: number
  currency: string
  status: string
  created_at: string
}

export interface PaperPosition {
  symbol: string
  name: string
  asset_class: AssetClass
  quantity: number
  is_short?: boolean
  avg_price_native: number
  avg_price_pln: number
  current_price_native: number
  current_price_pln: number
  market_value_pln: number
  cost_basis_pln: number
  unrealized_pnl_pln: number
  unrealized_pnl_pct: number
  currency: string
  opened_at?: string
  pending_limit_orders?: PaperLimitOrder[]
  broker_info?: BrokerPurchaseInfo | null
}

export interface PaperTrade {
  id: number
  symbol: string
  name: string
  asset_class: string
  side: string
  quantity: number
  price_native: number
  price_pln: number
  total_pln: number
  fee_pln: number
  currency: string
  created_at: string
}

export interface PaperClosedPosition {
  id: number
  symbol: string
  name: string
  asset_class: AssetClass
  quantity: number
  is_short: boolean
  entry_price_native: number
  exit_price_native: number
  entry_price_pln: number
  exit_price_pln: number
  cost_basis_pln: number
  proceeds_pln: number
  realized_pnl_pln: number
  realized_pnl_pct: number
  currency: string
  opened_at: string
  closed_at: string
}

export interface PaperPortfolio {
  cash_pln: number
  initial_cash_pln: number
  positions_value_pln: number
  total_equity_pln: number
  unrealized_pnl_pln: number
  realized_pnl_pln: number
  total_pnl_pln: number
  total_pnl_pct: number
  usd_pln_rate: number
  positions_count: number
  positions: PaperPosition[]
  closed_positions_count?: number
  closed_positions?: PaperClosedPosition[]
  limit_orders?: PaperLimitOrder[]
  recent_trades: PaperTrade[]
  quotes_available: number
}

export type { ChartPreset, ChartCandle, ChartResponse } from './chart'

export type RoiStrategy = 'buy_hold' | 'cycle' | 'dca' | 'cycle_dca'
export type RoiMode = 'forward' | 'backtest'

export interface RoiAssetInfo {
  symbol: string
  name: string
  asset_class: string
  region: string
  history_from: string
}

export interface RoiEquityPoint {
  time: number
  equity: number
  price?: number
  phase?: string
}

export interface RoiTrade {
  time: number
  action: 'buy' | 'sell' | string
  price: number
  amount: number
  units: number
  rationale: string
  phase: string
}

export interface RoiMilestone {
  year: number
  date: string
  base: number
  optimistic: number
  pessimistic: number
  roi_pct: number
}

export interface RoiSentiment {
  label: string
  score: number
  multiplier: number
  momentum_signal: string
  momentum_phase: string
  rationale: string
}

export interface RoiCurrentCycle {
  phase: string
  days_since_ath: number | null
  ath_date: string | null
  ath_price: number | null
  price: number
  historical_cagr_pct: number
  rationale: string
  price_phase: string
}

export interface RoiCalculateResult {
  mode?: RoiMode
  symbol: string
  name: string
  asset_class: string
  region: string
  strategy: RoiStrategy
  amount: number
  monthly_contribution?: number
  invested: number
  final_value: number
  final_optimistic?: number
  final_pessimistic?: number
  profit: number
  roi_pct: number
  cagr_pct: number
  max_drawdown_pct: number
  years: number
  data_start: string | null
  data_end: string | null
  bars: number
  cycle_source: string
  equity_curve: RoiEquityPoint[]
  optimistic_curve?: RoiEquityPoint[]
  pessimistic_curve?: RoiEquityPoint[]
  trades: RoiTrade[]
  price_series: { time: number; value: number }[]
  btc_cycle_aths: { date: string; price: number; label: string }[]
  milestones?: RoiMilestone[]
  sentiment?: RoiSentiment
  current_cycle?: RoiCurrentCycle
  disclaimer: string
  buy_hold?: {
    final_value: number
    roi_pct: number
    cagr_pct: number
    max_drawdown_pct: number
    equity_curve: RoiEquityPoint[]
  }
}

export interface RoiShowcaseCard {
  id: string
  featured: boolean
  symbol: string
  name: string
  strategy: RoiStrategy
  amount: number
  invested: number
  final_value: number
  profit: number
  roi_pct: number
  cagr_pct: number
  years: number
  data_start: string | null
  data_end: string | null
  buy_hold?: {
    final_value: number
    roi_pct: number
    cagr_pct: number
  }
}

export interface RoiShowcaseResult {
  amount: number
  years: number
  start: string
  end: string
  strategy: RoiStrategy
  cards: RoiShowcaseCard[]
  disclaimer: string
}

