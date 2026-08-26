import {
  AlertSettings,
  BitcoinCycleStatus,
  DashboardResponse,
  LiveQuote,
  NotificationStatus,
  PaperOrderRequest,
  PaperPortfolio,
  PaperPosition,
  PaperTrade,
  MacroCalendarMonth,
  MacroNewsFeed,
  TwilioConfig,
} from './types'
import type {
  AgentsReport,
  SuperOpportunitiesResponse,
  SuperOpportunity,
} from './types'
import { ChartPreset, ChartResponse, CHART_PRESETS } from './types/chart'
import { ApiError, type ApiErrorCode } from './i18n/apiErrors'

export { CHART_PRESETS }
export type { ChartPreset, ChartResponse }

export const API_BASE = '/api'

export type HealthResponse = {
  status: string
  scanner_running: boolean
  live_mode: boolean
  price_poll_seconds: number
  www: boolean
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' })
  if (!res.ok) throw new ApiError(apiErrorForStatus(res.status, 'noConnection'))
  return res.json() as Promise<HealthResponse>
}

function apiErrorForStatus(status: number, fallback: ApiErrorCode): ApiErrorCode {
  if (status === 429) return 'rateLimited'
  if (status === 400 || status === 422) return 'badRequest'
  if (status === 404) return 'noData'
  if (status === 502 || status === 503 || status >= 500) return 'serverUnavailable'
  return fallback
}

async function throwApiError(res: Response, fallback: ApiErrorCode): Promise<never> {
  let detail: string | undefined
  try {
    const body = await res.json()
    const d = body?.detail
    if (typeof d === 'string') detail = d
    else if (d && typeof d.message === 'string') detail = d.message
  } catch {
    /* ignore non-JSON bodies */
  }
  throw new ApiError(apiErrorForStatus(res.status, fallback), detail)
}

export async function fetchDashboard(): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/dashboard`)
  if (!res.ok) await throwApiError(res, 'fetchDashboard')
  return res.json()
}

export async function triggerScan(): Promise<{
  scanned: boolean
  background?: boolean
  already_running?: boolean
  opportunities_count: number
}> {
  const res = await fetch(`${API_BASE}/scan`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'scanFailed')
  return res.json()
}

export async function fetchNotificationStatus(): Promise<NotificationStatus> {
  const res = await fetch(`${API_BASE}/notifications/status`)
  if (!res.ok) await throwApiError(res, 'fetchNotifications')
  return res.json()
}

export async function saveAlertSettings(settings: AlertSettings): Promise<AlertSettings> {
  const res = await fetch(`${API_BASE}/notifications/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
  if (!res.ok) await throwApiError(res, 'saveSettings')
  return res.json()
}

export async function saveTwilioConfig(config: TwilioConfig): Promise<{ saved: boolean }> {
  const res = await fetch(`${API_BASE}/notifications/twilio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) await throwApiError(res, 'saveTwilio')
  return res.json()
}

export async function testNotifications(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/notifications/test`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'testNotifications')
  return res.json()
}

export async function fetchPaperPortfolio(): Promise<PaperPortfolio> {
  const res = await fetch(`${API_BASE}/paper/portfolio`)
  if (!res.ok) await throwApiError(res, 'fetchPortfolio')
  return res.json()
}

export type BinancePortfolioSync = {
  ok: boolean
  connected: boolean
  configured: boolean
  dry_run: boolean
  last_sync_at?: string
  paper_positions: Array<{ symbol: string; quantity: number; market_value_pln?: number }>
  binance_positions: Array<{ symbol: string; quantity: number; trade_url?: string }>
  drift: Array<{
    symbol: string
    paper_qty: number
    binance_qty: number
    delta_pct: number
    alert?: boolean
    trade_url?: string
  }>
  drift_count: number
  drift_alerts: number
  trade_links: Record<string, string>
}

export async function fetchBinancePortfolioSync(): Promise<BinancePortfolioSync> {
  const res = await fetch(`${API_BASE}/portfolio/binance-sync`)
  if (!res.ok) await throwApiError(res, 'fetchPortfolio')
  return res.json()
}

export async function fetchPaperMaxBuy(symbol: string): Promise<{ max_quantity: number }> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/paper/max-buy/${encoded}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function placePaperOrder(order: PaperOrderRequest): Promise<unknown> {
  const res = await fetch(`${API_BASE}/paper/order`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order),
  })
  if (!res.ok) await throwApiError(res, 'tradeFailed')
  return res.json()
}

export async function resetPaperPortfolio(): Promise<PaperPortfolio> {
  const res = await fetch(`${API_BASE}/paper/reset`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'resetFailed')
  return res.json()
}

export async function purgeAgentPaperPositions(force = false): Promise<unknown> {
  const qs = force ? '?force=true' : ''
  const res = await fetch(`${API_BASE}/paper/purge-agent-positions${qs}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'purgeAgentFailed')
  return res.json()
}

export async function fetchPaperPosition(symbol: string): Promise<PaperPosition | null> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/paper/position/${encoded}`)
  if (res.status === 404) return null
  if (!res.ok) await throwApiError(res, 'fetchPosition')
  return res.json()
}

export async function cancelPaperOrder(orderId: number): Promise<PaperPortfolio> {
  const res = await fetch(`${API_BASE}/paper/orders/${orderId}`, { method: 'DELETE' })
  if (!res.ok) await throwApiError(res, 'cancelOrder')
  const data = await res.json()
  return data.portfolio
}

/** @deprecated use cancelPaperOrder */
export const cancelPaperLimitOrder = cancelPaperOrder

export async function cancelAllPaperOrders(symbol?: string): Promise<PaperPortfolio> {
  const qs = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ''
  const res = await fetch(`${API_BASE}/paper/orders/cancel-all${qs}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'cancelAllOrders')
  const data = await res.json()
  return data.portfolio
}

export async function closePaperPosition(
  symbol: string,
  percent = 100,
): Promise<{ trade: PaperTrade; portfolio: PaperPortfolio }> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/paper/close/${encoded}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ percent }),
  })
  if (!res.ok) await throwApiError(res, 'closePosition')
  return res.json()
}

export async function fetchPaperTrades(symbol: string): Promise<PaperTrade[]> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/paper/trades/${encoded}`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchQuote(symbol: string): Promise<LiveQuote> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/markets/quote/${encoded}`, { cache: 'no-store' })
  if (!res.ok) await throwApiError(res, 'fetchPrice')
  return res.json()
}

export async function fetchChart(symbol: string, range: ChartPreset = '3M'): Promise<ChartResponse> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/markets/chart/${encoded}?range=${range}`)
  if (!res.ok) await throwApiError(res, 'fetchChart')
  return res.json()
}

export async function fetchChartPresets(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/markets/chart-presets`)
  if (!res.ok) return CHART_PRESETS
  return res.json()
}

export async function fetchMacroCalendar(year: number, month: number, lang?: string): Promise<MacroCalendarMonth> {
  const qs = new URLSearchParams({ year: String(year), month: String(month) })
  if (lang) qs.set('lang', lang)
  const res = await fetch(`${API_BASE}/news/calendar?${qs}`)
  if (!res.ok) await throwApiError(res, 'fetchCalendar')
  return res.json()
}

export async function fetchMacroNews(category?: string, limit = 100, lang?: string): Promise<MacroNewsFeed> {
  const qs = new URLSearchParams()
  if (category && category !== 'all') qs.set('category', category)
  qs.set('limit', String(limit))
  if (lang) qs.set('lang', lang)
  const res = await fetch(`${API_BASE}/news/macro?${qs}`)
  if (!res.ok) await throwApiError(res, 'fetchNews')
  return res.json()
}

export async function refreshMacroNews(lang?: string): Promise<MacroNewsFeed> {
  const qs = lang ? `?lang=${encodeURIComponent(lang)}` : ''
  const res = await fetch(`${API_BASE}/news/macro/refresh${qs}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'refreshNews')
  return res.json()
}

export interface SocialDeskStatus {
  enabled: boolean
  dry_run: boolean
  auto_post: boolean
  cooldown_minutes: number
  max_per_cycle: number
  public_base_url: string | null
  x_configured: boolean
  linkedin_configured: boolean
}

export interface SocialPost {
  id: number
  platform: string
  news_id: string
  url: string | null
  title: string
  body: string
  media_path: string | null
  status: string
  error: string | null
  external_id: string | null
  created_at: string
  posted_at: string | null
}

export async function fetchSocialStatus(): Promise<SocialDeskStatus> {
  const res = await fetch(`${API_BASE}/social/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchSocialPosts(limit = 20): Promise<{
  count: number
  posts: SocialPost[]
  status: SocialDeskStatus
}> {
  const res = await fetch(`${API_BASE}/social/posts?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function publishSocialPost(postId: number): Promise<{ ok: boolean; post: SocialPost }> {
  const res = await fetch(`${API_BASE}/social/posts/${postId}/publish`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'badRequest')
  return res.json()
}

export interface PredatorStatus {
  enabled: boolean
  configured: boolean
  notify: boolean
  chat_id_filter?: string | null
  bot?: { id?: number; username?: string; first_name?: string } | null
  free_setup?: string
  recent?: PredatorSignal[]
}

export interface PredatorSignal {
  id: number
  tg_message_id?: number | null
  chat_id: string
  symbol: string
  action: string
  confidence: number
  reason: string
  raw_text?: string
  created_at: string
}

export async function fetchPredatorStatus(): Promise<PredatorStatus> {
  const res = await fetch(`${API_BASE}/predator/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchPredatorSignals(limit = 30): Promise<{ count: number; signals: PredatorSignal[] }> {
  const res = await fetch(`${API_BASE}/predator/signals?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function pollPredatorFeed(): Promise<{ ok: boolean; updates: number; new: number }> {
  const res = await fetch(`${API_BASE}/predator/poll`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'badRequest')
  return res.json()
}

export interface AiStatus {
  enabled: boolean
  llm_configured: boolean
  model: string
  provider?: string
  base_url?: string
  requires_api_key?: boolean
  features: string[]
  knowledge_entries: number
  learning_notes: number
}

export interface AiChatRequest {
  message: string
  session_id?: string
  locale?: string
  symbol?: string
}

export interface AiChatResponse {
  session_id: string
  reply: string
  message_id: number
  tools_used: string[]
  tool_results: Record<string, unknown>[]
  critic_score?: number | null
  llm_active: boolean
  tool_count: number
  focus_symbol?: string | null
  desk_ui?: Record<string, unknown> | null
}

export interface AiMessage {
  id: number
  role: string
  content: string
  meta?: Record<string, unknown> | null
  created_at: string
}

export interface AiFeedbackRequest {
  session_id: string
  message_id?: number
  rating: number
  correction?: string
  question?: string
  answer?: string
}

export interface AiAnalyzeResponse {
  symbol: string
  summary: string
  tools: { tool: string; result: Record<string, unknown> }[]
  llm_active: boolean
  focus_symbol?: string | null
  desk_ui?: Record<string, unknown> | null
}

export async function fetchAiStatus(): Promise<AiStatus> {
  const res = await fetch(`${API_BASE}/ai/status`)
  if (!res.ok) await throwApiError(res, 'fetchAiStatus')
  return res.json()
}

export async function postAiChat(body: AiChatRequest): Promise<AiChatResponse> {
  const res = await fetch(`${API_BASE}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await throwApiError(res, 'aiChatFailed')
  return res.json()
}

export async function postAiFeedback(body: AiFeedbackRequest): Promise<{ saved: boolean }> {
  const res = await fetch(`${API_BASE}/ai/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await throwApiError(res, 'aiFeedbackFailed')
  return res.json()
}

export async function fetchAiHistory(sessionId: string, limit = 40): Promise<{ session_id: string; messages: AiMessage[] }> {
  const qs = new URLSearchParams({ session_id: sessionId, limit: String(limit) })
  const res = await fetch(`${API_BASE}/ai/history?${qs}`)
  if (!res.ok) await throwApiError(res, 'aiHistoryFailed')
  return res.json()
}

export async function postAiAnalyze(symbol: string, lang?: string): Promise<AiAnalyzeResponse> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const qs = lang ? `?lang=${encodeURIComponent(lang)}` : ''
  const res = await fetch(`${API_BASE}/ai/analyze/${encoded}${qs}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'aiAnalyzeFailed')
  return res.json()
}

export async function fetchMarketAssessment(symbol: string): Promise<import('./types').AssetCycleAssessment> {
  const encoded = symbol.split('/').map(encodeURIComponent).join('/')
  const res = await fetch(`${API_BASE}/markets/assessment/${encoded}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function fetchRoiAssets(): Promise<import('./types').RoiAssetInfo[]> {
  const res = await fetch(`${API_BASE}/roi/assets`)
  if (!res.ok) await throwApiError(res, 'roiAssetsFailed')
  return res.json()
}

export async function fetchRoiShowcase(years = 10, amount = 10000): Promise<import('./types').RoiShowcaseResult> {
  const qs = `?years=${years}&amount=${amount}`
  const res = await fetch(`${API_BASE}/roi/showcase${qs}`)
  if (!res.ok) await throwApiError(res, 'roiShowcaseFailed')
  return res.json()
}

export type AgentTelemetryPoint = {
  ts: string
  time: number
  agent_nav: number
  spx_nav: number
  agent_ret_pct: number
  spx_ret_pct: number
  n_long: number
  n_universe: number
  health_ok: boolean
  portfolio_equity_pln?: number | null
  signal_nav?: number | null
  inception_nav?: number | null
  source?: string
}

export type AgentTelemetryResponse = {
  range: string
  points: AgentTelemetryPoint[]
  last: AgentTelemetryPoint | null
  max_drawdown_pct: number
  vs_spx_nav: number | null
  count: number
  metric?: string
  disclaimer?: string
  baseline_started_at?: string
  live?: {
    portfolio_equity_pln?: number
    inception_nav?: number
    vs_spx_nav?: number | null
  } | null
}

export async function fetchAgentTelemetry(
  range: '7d' | '30d' | '90d' | 'all' = '30d',
): Promise<AgentTelemetryResponse> {
  const res = await fetch(`${API_BASE}/telemetry/agent-vs-sp500?range=${range}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export type CoordinatorDeskStatus = {
  ok?: boolean
  last_tick_at?: string | null
  last_error?: string | null
  warming_up?: boolean
  link_guard?: {
    ok?: boolean
    missing_chain_axiom?: number
    bad_4meme?: number
  }
}

export type CoordinatorHealth = {
  ok: boolean
  at?: string
  startup_grace?: boolean
  desks?: {
    launch?: CoordinatorDeskStatus
    axiom?: CoordinatorDeskStatus
    fomo?: CoordinatorDeskStatus
  }
  warnings?: string[]
  hard_errors?: string[]
  desks_stale?: string[]
  binance_bot?: { ok?: boolean; connected?: boolean }
}

export async function fetchCoordinatorHealth(): Promise<CoordinatorHealth> {
  const res = await fetch(`${API_BASE}/coordinator/health`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export type ProgramUsBacktestResponse = {
  final_value?: number
  cagr_pct?: number
  max_drawdown_pct?: number
  disclaimer?: string
  equity_curve?: { time: number; equity: number }[]
  buy_hold?: {
    final_value?: number
    equity_curve?: { time: number; equity: number }[]
  }
  program?: {
    agent_final?: number
    buy_hold_final?: number
    ratio_agent_vs_bh?: number | null
    disclaimer?: string
    trades_count?: number
  }
}

export async function fetchProgramUs1995(amount = 1000): Promise<ProgramUsBacktestResponse> {
  const res = await fetch(`${API_BASE}/roi/program-us-1995?amount=${amount}`)
  if (!res.ok) await throwApiError(res, 'roiCalculateFailed')
  return res.json()
}

export async function fetchSeasonalityHealth(refresh = false): Promise<Record<string, unknown>> {
  const qs = refresh ? '?refresh=true' : ''
  const res = await fetch(`${API_BASE}/cycles/seasonality-health${qs}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export type IntramonthDay = {
  day: number
  avg_return_pct: number | null
  bias: string
  n: number
  week: number
}

export type IntramonthWeek = {
  week: number
  label: string
  day_range: string
  avg_return_pct: number | null
  bias: string
  n: number
}

export type IntramonthResponse = {
  universe: 'us' | 'btc'
  universe_label: string
  month: number
  month_name_pl: string
  days: IntramonthDay[]
  weeks: IntramonthWeek[]
  strongest_days: IntramonthDay[]
  weakest_days: IntramonthDay[]
  note: string
}

export async function fetchIntramonth(
  month: number,
  universe: 'us' | 'btc' = 'us',
): Promise<IntramonthResponse> {
  const res = await fetch(
    `${API_BASE}/cycles/intramonth?month=${month}&universe=${universe}`,
  )
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export type GlobalBookEntry = {
  id: string
  horizon: 'monthly' | 'weekly' | 'yearly'
  slot: number
  slot_label: string
  side: 'bid' | 'ask'
  avg_return_pct: number
  markets: string[]
  markets_n: number
  markets_total: number
  reproduction_score: number
  status: 'adopted' | 'watch' | 'rejected'
  rank: number
}

export type GlobalCycleBookResponse = {
  generated_at?: string
  meta: Record<string, unknown>
  pairwise_month_corr: Record<string, number>
  profiles: Record<
    string,
    {
      universe: string
      label: string
      symbols_included: number
      symbols_total: number
      months: Array<{
        month: number
        label: string
        avg_return_pct: number | null
        n: number
        bias: string
      }>
      weeks: Array<{
        week: number
        label: string
        day_range: string
        avg_return_pct: number | null
        n: number
        bias: string
      }>
      yearly: Record<string, unknown>
    }
  >
  order_book: GlobalBookEntry[]
  adopted: GlobalBookEntry[]
  note: string
}

export async function fetchGlobalCycleBook(
  status: 'all' | 'adopted' | 'watch' | 'rejected' = 'all',
): Promise<GlobalCycleBookResponse> {
  const res = await fetch(`${API_BASE}/cycles/global-book?status=${status}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export type CalendarMonthCell = {
  month: number
  label_pl: string
  label_en: string
  avg_return_pct: number | null
  median_pct?: number | null
  win_rate?: number | null
  n: number
  bias: string
  source?: string
}

export type InstrumentCalendarResponse = {
  symbol: string
  name: string
  asset_class: string
  region: string
  available: boolean
  source: string
  months: CalendarMonthCell[]
  strongest_months: CalendarMonthCell[]
  weakest_months: CalendarMonthCell[]
  pump_score: number | null
  narrative: string | null
  note: string
}

export type MonthPumpEntry = {
  symbol: string
  name: string
  asset_class: string
  region: string
  avg_return_pct: number | null
  median_pct?: number | null
  win_rate?: number | null
  n: number
  bias: string
}

export type MonthPumpsResponse = {
  month: number
  label_pl: string
  label_en: string
  asset_class?: string | null
  region?: string | null
  pumped: MonthPumpEntry[]
  drained: MonthPumpEntry[]
  universe_n: number
  note: string
}

export type MonthPumpSnippet = {
  month: number
  label_pl: string
  label_en: string
  text: string
  pumped: MonthPumpEntry[]
  drained: MonthPumpEntry[]
}

export type CalendarSearchHit = {
  symbol: string
  name: string
  asset_class: string
  region: string
  has_calendar: boolean
}

export async function fetchInstrumentCalendar(symbol: string): Promise<InstrumentCalendarResponse> {
  const res = await fetch(
    `${API_BASE}/cycles/instrument-calendar?symbol=${encodeURIComponent(symbol)}`,
  )
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function fetchMonthPumps(
  month: number,
  opts?: { class?: string; region?: string; limit?: number },
): Promise<MonthPumpsResponse> {
  const qs = new URLSearchParams({ month: String(month) })
  if (opts?.class) qs.set('class', opts.class)
  if (opts?.region) qs.set('region', opts.region)
  if (opts?.limit) qs.set('limit', String(opts.limit))
  const res = await fetch(`${API_BASE}/cycles/month-pumps?${qs}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function fetchMonthPumpSnippet(month: number, topN = 3): Promise<MonthPumpSnippet> {
  const res = await fetch(
    `${API_BASE}/cycles/month-pumps/snippet?month=${month}&top_n=${topN}`,
  )
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function fetchCalendarSearch(q: string, limit = 20): Promise<CalendarSearchHit[]> {
  const res = await fetch(
    `${API_BASE}/cycles/calendar-search?q=${encodeURIComponent(q)}&limit=${limit}`,
  )
  if (!res.ok) await throwApiError(res, 'noData')
  const data = await res.json()
  return data.results ?? []
}

export async function calculateRoi(body: {
  symbol: string
  amount: number
  strategy: string
  mode?: 'forward' | 'backtest'
  years?: number
  monthly_contribution?: number
  start?: string
  end?: string
  compare_buy_hold?: boolean
}): Promise<import('./types').RoiCalculateResult> {
  const res = await fetch(`${API_BASE}/roi/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await throwApiError(res, 'roiCalculateFailed')
  return res.json()
}

export async function fetchPublicLive(lang?: string): Promise<PublicLiveDigest> {
  const qs = lang ? `?lang=${encodeURIComponent(lang)}` : ''
  const res = await fetch(`${API_BASE}/public/live${qs}`)
  if (!res.ok) await throwApiError(res, 'fetchLiveFailed')
  return res.json()
}

export async function fetchGrowthPackages(): Promise<GrowthPackage[]> {
  const res = await fetch(`${API_BASE}/growth/packages`)
  if (!res.ok) await throwApiError(res, 'fetchGrowthFailed')
  return res.json()
}


export async function fetchBackupStatus(): Promise<{
  ui_auto_refresh_seconds?: number
  auto_backup_enabled?: boolean
  auto_backup_interval_seconds?: number
  [key: string]: unknown
}> {
  const res = await fetch(`${API_BASE}/backup/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function subscribeNewsletter(email: string, locale?: string, source = 'web'): Promise<{ ok: boolean }> {
  const res = await fetch(`${API_BASE}/growth/newsletter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, locale, source }),
  })
  if (!res.ok) await throwApiError(res, 'newsletterFailed')
  return res.json()
}

export async function submitBusinessLead(body: {
  name: string
  email: string
  company?: string
  package?: string
  message?: string
  locale?: string
}): Promise<{ ok: boolean; id?: number }> {
  const res = await fetch(`${API_BASE}/growth/contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await throwApiError(res, 'contactFailed')
  return res.json()
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const res = await fetch(`${API_BASE}/growth/watchlist`)
  if (!res.ok) await throwApiError(res, 'fetchGrowthFailed')
  return res.json()
}

export async function voteWatchlist(symbol: string, name?: string): Promise<{ ok: boolean; votes: number }> {
  const res = await fetch(`${API_BASE}/growth/watchlist/vote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, name }),
  })
  if (!res.ok) await throwApiError(res, 'fetchGrowthFailed')
  return res.json()
}

export async function fetchEmbedCycle(): Promise<EmbedCyclePayload> {
  const res = await fetch(`${API_BASE}/embed/cycle`)
  if (!res.ok) await throwApiError(res, 'embedFailed')
  return res.json()
}

export async function fetchPearlStatus() {
  const res = await fetch(`${API_BASE}/pearl/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchPearlFinds(agentId?: string) {
  const qs = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ''
  const res = await fetch(`${API_BASE}/pearl/finds${qs}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function runPearlHunt(agent: 'equity' | 'crypto' | 'both' = 'both') {
  const res = await fetch(`${API_BASE}/pearl/run?agent=${agent}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export type FomoTrader = {
  handle: string
  rank: number
  pnl?: number | null
  win_rate?: number | null
  trades?: number
  updated_at?: string
}

export type FomoEvent = {
  event_id: string
  handle: string
  action: string
  mint: string
  symbol: string
  chain: string
  usd_amount?: number | null
  ts_unix?: number
  created_at?: string
}

export type FomoStatus = {
  enabled: boolean
  mode?: 'live' | 'degraded' | 'idle' | string
  needs_api_key?: boolean
  has_api_key?: boolean
  top_n?: number
  timeframe?: string
  interval_seconds?: number
  last_tick_at?: string | null
  last_error?: string | null
  traders_count?: number
  events_count?: number
  source?: string
  usage?: Record<string, unknown>
  telegram?: {
    enabled?: boolean
    configured_chats?: string[]
    listen_mode?: string
    shared_bot?: boolean
    hint?: string
  }
  family?: {
    traders_with_bags?: number
    positions_open?: number
    positions_all?: number
    open_usd_approx?: number
  }
}

export async function fetchFomoStatus(): Promise<FomoStatus> {
  const res = await fetch(`${API_BASE}/fomo/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchFomoTop(limit = 30): Promise<{ traders: FomoTrader[] }> {
  const res = await fetch(`${API_BASE}/fomo/top?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchFomoEvents(
  limit = 50,
  side?: 'buy' | 'sell',
): Promise<{ events: FomoEvent[] }> {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (side) qs.set('side', side)
  const res = await fetch(`${API_BASE}/fomo/events?${qs}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function runFomoTick(force = false) {
  const res = await fetch(`${API_BASE}/fomo/run?force=${force ? 'true' : 'false'}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function registerFomoKey(agentName = 'cyclical-trader-fomo-ghost') {
  const res = await fetch(`${API_BASE}/fomo/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_name: agentName }),
  })
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export type FomoBag = {
  handle: string
  mint: string
  symbol: string
  chain: string
  status: string
  net_usd?: number | null
  buy_usd?: number | null
  sell_usd?: number | null
  buys?: number
  sells?: number
  last_ts?: number | null
  last_action?: string | null
  family?: string
}

export type FomoFamilySummary = {
  family?: string
  traders_with_bags?: number
  positions_open?: number
  positions_all?: number
  open_usd_approx?: number
}

export async function fetchFomoFamily(limit = 100): Promise<{
  bags: FomoBag[]
  summary?: FomoFamilySummary
}> {
  const res = await fetch(`${API_BASE}/fomo/family?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchFomoBags(
  limit = 100,
  includeClosed = false,
): Promise<{ bags: FomoBag[]; summary?: FomoFamilySummary }> {
  const qs = new URLSearchParams({
    limit: String(limit),
    include_closed: includeClosed ? 'true' : 'false',
  })
  const res = await fetch(`${API_BASE}/fomo/bags?${qs}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export type AxiomStatus = {
  enabled: boolean
  brand?: string
  tagline?: string
  interval_seconds?: number
  last_tick_at?: string | null
  last_error?: string | null
  pulse_count?: number
  positions_open?: number
  positions_all?: number
  pulse_source?: string
  axiom_auth?: boolean
  wallets_tracked?: number
  kar_digital_wallet?: string | null
  kar_digital_configured?: boolean
  include_closed?: boolean
}

export type AxiomPulseMarket = {
  mint: string
  symbol: string
  name?: string
  chain: string
  pair_address?: string | null
  price_usd?: number | null
  liquidity_usd?: number | null
  market_cap_usd?: number | null
  volume_24h?: number | null
  change_1h?: number | null
  change_24h?: number | null
  image_url?: string | null
  url?: string | null
  source?: string
  updated_at?: string
}

export type AxiomPosition = {
  position_id: string
  owner: string
  owner_kind: string
  mint: string
  symbol: string
  chain: string
  status: string
  usd_size?: number | null
  amount?: number | null
  last_ts?: number | null
  url?: string | null
  image_url?: string | null
  updated_at?: string
}

export async function fetchAxiomStatus(): Promise<AxiomStatus> {
  const res = await fetch(`${API_BASE}/axiom/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchAxiomPulse(limit = 80): Promise<{ markets: AxiomPulseMarket[] }> {
  const res = await fetch(`${API_BASE}/axiom/pulse?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchAxiomPositions(
  limit = 200,
  status: 'open' | 'closed' | 'all' = 'all',
): Promise<{ positions: AxiomPosition[] }> {
  const qs = new URLSearchParams({ limit: String(limit), status })
  const res = await fetch(`${API_BASE}/axiom/positions?${qs}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function runAxiomTick() {
  const res = await fetch(`${API_BASE}/axiom/run`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export type LaunchCandidate = {
  candidate_id: string
  mint: string
  symbol: string
  name?: string
  chain: string
  dex_id?: string
  pair_address?: string
  market_cap?: number | null
  liq_usd?: number | null
  age_hours?: number | null
  tier: string
  score?: number
  source?: string
  url?: string
  launchpad_url?: string
  image_url?: string | null
  tags?: string[]
  updated_at?: string
}

export type LaunchStatus = {
  enabled: boolean
  flagship?: boolean
  brand?: string
  tagline?: string
  entry_note?: string
  interval_seconds?: number
  thresholds?: Record<string, number>
  chains?: string[]
  last_tick_at?: string | null
  last_error?: string | null
  counts?: { all?: number; seed?: number; fresh?: number; early?: number; watch?: number }
  whispers_count?: number
  whispers_enabled?: boolean
  traders_count?: number
  sources?: string[]
  note?: string
}

export type MemeWhisper = {
  id: string
  author: string
  text: string
  url?: string
  ts_unix?: number
  keywords?: string[]
  source?: string
  created_at?: string
}

export type LaunchTrader = {
  wallet: string
  rank: number
  score?: number
  buys?: number
  source?: string
  updated_at?: string
}

export type LaunchTraderEvent = {
  event_id: string
  wallet: string
  action: string
  mint: string
  symbol: string
  chain: string
  usd_amount?: number | null
  ts_unix?: number
  source?: string
}

export async function fetchLaunchStatus(): Promise<LaunchStatus> {
  const res = await fetch(`${API_BASE}/launch/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchLaunchCandidates(
  tier: 'seed' | 'fresh' | 'early' | 'watch' | 'all' = 'seed',
  limit = 50,
): Promise<{ candidates: LaunchCandidate[] }> {
  const qs = new URLSearchParams({ tier, limit: String(limit) })
  const res = await fetch(`${API_BASE}/launch/candidates?${qs}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function runLaunchScoutTick() {
  const res = await fetch(`${API_BASE}/launch/run`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchLaunchWhispers(limit = 20): Promise<{ whispers: MemeWhisper[] }> {
  const res = await fetch(`${API_BASE}/launch/whispers?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchLaunchTraders(limit = 30): Promise<{ traders: LaunchTrader[] }> {
  const res = await fetch(`${API_BASE}/launch/traders?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchLaunchTraderEvents(limit = 40): Promise<{ events: LaunchTraderEvent[] }> {
  const res = await fetch(`${API_BASE}/launch/trader-events?limit=${limit}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchExecutionStatus() {
  const res = await fetch(`${API_BASE}/execution/status`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function fetchExecutionProposals(limit = 50, status?: string) {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (status) qs.set('status', status)
  const res = await fetch(`${API_BASE}/execution/proposals?${qs}`)
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function approveExecutionProposal(id: number) {
  const res = await fetch(`${API_BASE}/execution/proposals/${id}/approve`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'badRequest')
  return res.json()
}

export async function runExecutionAgent(force = false) {
  const res = await fetch(`${API_BASE}/execution/run?force=${force}`, { method: 'POST' })
  if (!res.ok) await throwApiError(res, 'serverUnavailable')
  return res.json()
}

export async function patchExecutionSettings(patch: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/execution/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!res.ok) await throwApiError(res, 'badRequest')
  return res.json()
}

export interface PublicLiveDigest {
  fetched_at: string
  status: string
  bitcoin_cycle: BitcoinCycleStatus | null
  presidential_cycle: {
    president?: string
    current_year?: string
    year_number?: number
    signal?: string
    rationale?: string
    current_year_expected_return_pct?: number
  } | null
  top_opportunities: {
    symbol: string
    name: string
    action: string
    confidence: number
    phase: string
    price: number
    rationale: string
  }[]
  news: {
    id: string
    title: string
    source: string
    category: string
    url?: string | null
    age_minutes?: number | null
    image_url?: string | null
  }[]
  watchlist: WatchlistItem[]
  disclaimer: string
}

export interface WatchlistItem {
  symbol: string
  name: string
  votes: number
  updated_at: string
  community?: import('./types').InstrumentCommunity | null
}

export interface GrowthPackage {
  id: string
  name: string
  price: string
  bullets: string[]
}





export interface EmbedCyclePayload {
  brand: string
  symbol: string
  phase: string
  signal: string
  days_since_ath: number
  ath_price: number
  ath_date: string
  current_price: number
  progress_pct: number
  rationale: string
  embed_url: string
  live_url: string
  disclaimer: string
}


export async function fetchSuperOpportunities(
  minScore = 0,
): Promise<SuperOpportunitiesResponse> {
  const res = await fetch(`${API_BASE}/super-opportunities?min_score=${minScore}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function fetchSuperOpportunity(symbol: string): Promise<SuperOpportunity> {
  const res = await fetch(`${API_BASE}/super-opportunities/${encodeURIComponent(symbol)}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}

export async function fetchAgentsReport(refresh = false): Promise<AgentsReport> {
  const q = refresh ? '?refresh=true' : ''
  const res = await fetch(`${API_BASE}/singularity${q}`)
  if (!res.ok) await throwApiError(res, 'noConnection')
  return res.json()
}

export async function fetchWhaleFlows(force = false): Promise<{
  count: number
  items: unknown[]
  by_symbol: Record<string, unknown>
}> {
  const q = force ? '?force=true' : ''
  const res = await fetch(`${API_BASE}/whale-flows${q}`)
  if (!res.ok) await throwApiError(res, 'noData')
  return res.json()
}
