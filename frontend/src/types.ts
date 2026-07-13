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
  signal: SignalAction
  confidence: number
  rationale: string
  updated_at: string
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
}

export interface AlertSettings {
  phone: string
  sms_enabled: boolean
  push_enabled: boolean
  min_confidence: number
  alert_on_signal_change: boolean
  alert_on_new_opportunity: boolean
}

export interface NotificationStatus {
  push_configured: boolean
  sms_configured: boolean
  vapid_public_key: string
  push_subscriptions: number
  settings: AlertSettings
}

export type { ChartPreset, ChartCandle, ChartResponse } from './types/chart'
