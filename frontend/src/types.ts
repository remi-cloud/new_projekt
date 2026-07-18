export type AssetClass = 'crypto' | 'stock' | 'index' | 'bond' | 'commodity' | 'forex'
export type SignalAction = 'buy' | 'sell' | 'hold' | 'watch'
export type CyclePhase = 'bear' | 'accumulation' | 'bull' | 'distribution' | 'neutral'

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

export interface DashboardResponse {
  bitcoin_cycle: BitcoinCycleStatus
  presidential_cycle: PresidentialCycleStatus
  opportunities: Opportunity[]
  monitored_assets: AssetQuote[]
  last_scan_at: string | null
  scanner_running: boolean
}

export interface ScanLogEntry {
  id: number
  scanned_at: string
  opportunities_count: number
  changes_count: number
}

export interface SignalChange {
  id: number
  scan_id: number
  symbol: string
  name: string
  asset_class: string
  previous_action: string | null
  new_action: string
  previous_confidence: number | null
  new_confidence: number
  cycle_source: string
  phase: string
  price: number
  created_at: string
}

export interface HistoryResponse {
  scans: ScanLogEntry[]
  changes: SignalChange[]
  recent_opportunities: Opportunity[]
}
