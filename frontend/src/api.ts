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

export interface AiStatus {
  enabled: boolean
  llm_configured: boolean
  model: string
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
