export type AssetClass = 'crypto' | 'stock' | 'index' | 'bond' | 'commodity' | 'forex'
export type SignalAction = 'buy' | 'sell' | 'hold' | 'watch'
export type CyclePhase = 'bear' | 'accumulation' | 'bull' | 'distribution' | 'neutral'

export interface AlphaModelStatus {
  reference_date: string
  reference_price: number
  current_price: number
  days_since_reference: number
  phase_a_end_day: number
  phase_b_end_day: number
  phase: CyclePhase
  phase_progress_pct: number
  days_remaining_in_phase: number
  signal: SignalAction
  rationale: string
}

export interface BetaModelStatus {
  period_start: string
  period_end: string
  current_phase: string
  phase_number: number
  days_into_phase: number
  days_remaining_in_phase: number
  phase_progress_pct: number
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
  region?: string
  region_label?: string
  live?: boolean
  quote_source?: string
}

export interface MarketRegionCount {
  id: string
  label: string
  count: number
  live_count: number
}

export interface MarketsResponse {
  generated_at: string
  count: number
  global_count: number
  live_count: number
  regions: MarketRegionCount[]
  items: AssetQuote[]
}

export interface EconomicEvent {
  event_id: string
  title: string
  country: string
  impact: string
  impact_rank: number
  event_at: string
  forecast: string
  previous: string
  actual: string
  source: string
}

export interface BroadcastSetup {
  symbol: string
  name: string
  side: string
  confidence: number
  super_score: number | null
  price: number
  rationale: string
  path: string
}

export interface BroadcastResponse {
  visible: boolean
  mode?: 'live' | 'breaking' | string
  live_count?: number
  quote_count?: number
  cycle_minutes: number
  show_minutes: number
  seconds_remaining: number
  next_show_in_seconds: number
  headline: string
  setup: BroadcastSetup | null
  events: EconomicEvent[]
  lines: string[]
  sources: string[]
  generated_at: string
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
  alpha_model: AlphaModelStatus
  beta_model: BetaModelStatus
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

export interface WatchlistItem {
  symbol: string
  name: string
  asset_class: AssetClass
  source: string
  enabled: boolean
  created_at?: string
}

export interface CatalogAsset {
  symbol: string
  name: string
  asset_class: AssetClass
  source: string
}

export interface WatchlistResponse {
  items: WatchlistItem[]
  catalog: CatalogAsset[]
}

export interface AlertSettings {
  enabled: boolean
  ntfy_server: string
  ntfy_topic: string
  webhook_url: string
  min_confidence: number
  actions: string[]
  alert_on_first_seen: boolean
}

export interface AlertLogEntry {
  id: number
  channel: string
  status: string
  message: string
  detail: string | null
  created_at: string
}

export interface TradeLevels {
  side: string
  entry: number
  stop_loss: number
  take_profit_1: number
  take_profit_2: number
  risk_reward: number
  note: string
}

export interface HeatmapBin {
  price: number
  long_intensity: number
  short_intensity: number
  dominant: 'long' | 'short' | string
  intensity: number
}

export interface LiquidationHeatmap {
  price: number
  range_low: number
  range_high: number
  bins: HeatmapBin[]
  columns?: HeatmapBin[][]
  max_intensity: number
}

export interface LiqPathPoint {
  t: number
  price: number
  role: string
  intensity: number
}

export interface LiqAnchor {
  price: number
  role: string
  label: string
  t: number
  liq_side?: string
}

export interface LiqPrediction {
  direction: string
  confidence: number
  summary: string
  target_price: number
  target_side: string
  target_intensity: number
  pull_up: number
  pull_down: number
  momentum: number
  path: LiqPathPoint[]
  anchors: LiqAnchor[]
  features?: Record<string, number>
}

export interface AiTradeFactor {
  name: string
  side: string
  weight: number
  detail: string
}

export interface AiTradeSignal {
  signal: 'kup' | 'sprzedaj' | 'czekaj' | string
  label: string
  confidence: number
  buy_score: number
  sell_score: number
  aligned: boolean
  conflict: boolean
  summary: string
  factors: AiTradeFactor[]
  verdict_detail: string
}

export interface SuperOpportunity {
  symbol: string
  name: string
  asset_class: AssetClass
  action: SignalAction
  cycle_confidence: number
  super_score: number
  is_super: boolean
  cycle_source: string
  phase: string
  price: number
  bid: number | null
  ask: number | null
  spread_pct: number | null
  book_source: string | null
  levels: TradeLevels
  heatmap: LiquidationHeatmap
  prediction?: LiqPrediction | null
  ai_signal?: AiTradeSignal | null
  whale?: WhaleFlowSignal | null
  reasons: string[]
  rationale: string
  updated_at: string
}

export interface WhaleFlowSignal {
  symbol: string
  bias: 'accumulate' | 'distribute' | 'neutral' | string
  side_hint: string
  strength: number
  score: number
  summary: string
  factors: string[]
  updated_at?: string | null
}

export interface SuperOpportunitiesResponse {
  generated_at: string
  count: number
  super_count: number
  long_count?: number
  short_count?: number
  items: SuperOpportunity[]
  supers: SuperOpportunity[]
  scanner_last_scan_at: string | null
}

export interface AgentScoutInfo {
  id: string
  label: string
  symbols: number
  region: string
}

export interface AgentVerdictInfo {
  symbol: string
  name: string
  accepted: boolean
  confidence: number
  summary: string
  scout_ids: string[]
  factors: Array<{ name: string; detail: string; weight?: number }>
}

export interface AgentsReport {
  ready?: boolean
  pipeline?: string
  long_scouts?: AgentScoutInfo[]
  short_scouts?: AgentScoutInfo[]
  counts?: {
    long_scouts: number
    short_scouts: number
    equal: boolean
  }
  specialists?: Array<{ id: string; label: string }>
  orchestrator?: { id: string; label: string }
  last_scan_at?: string | null
  last_stats?: Record<string, unknown>
  opportunities?: { total: number; long: number; short: number }
  long_verdicts?: AgentVerdictInfo[]
  short_verdicts?: AgentVerdictInfo[]
  long_findings_sample?: Array<{
    scout_id: string
    symbol: string
    confidence: number
    rationale: string
  }>
  short_findings_sample?: Array<{
    scout_id: string
    symbol: string
    confidence: number
    rationale: string
  }>
}
