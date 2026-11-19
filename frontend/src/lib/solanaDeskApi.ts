import { apiFetch } from './deskAuth'
import { API_BASE } from './sameOrigin'

export type SolanaAgent = {
  seen?: number
  passed?: number
  rejected?: number
  pending_risk?: number
  reasons?: Record<string, number>
  entries?: number
  skipped?: number
  exits?: number
  note?: string
}

export type SolanaStatus = {
  mode: string
  running: boolean
  kill_switch: boolean
  real_trading_flag: boolean
  wallet_configured: boolean
  real_trading_active: boolean
  rpc_configured: boolean
  armed: boolean
  lock_reason: string
  route?: string
  cash_sol: number
  equity_sol: number
  equity_usd: number
  sol_usd: number
  net_pnl_sol: number
  realized_pnl_sol: number
  fees_sol: number
  win_rate: number
  closed_trades: number
  wins: number
  open_positions: number
  max_drawdown: number
  last_tick_at: string
  last_error: string
  worker_online: boolean
  settings: Record<string, number>
  agents: Record<string, SolanaAgent>
  positions: Array<{
    mint: string
    symbol: string
    venue: string
    status: string
    entry_price: number | null
    last_price: number | null
    size_sol: number
    unrealized_pnl_sol: number
  }>
  report: {
    title?: string
    day?: string
    pnl_sol?: number
    fees_sol?: number
    closed_trades?: number
    win_rate?: number
    max_drawdown?: number
    note?: string
  } | null
}

export type SolanaJournal = {
  trades: Array<{
    id: number
    opened_at: string
    closed_at: string | null
    mint: string
    symbol: string
    status: string
    entry_price: number | null
    exit_price: number | null
    entry_fee_sol: number
    exit_fee_sol: number
    entry_slippage: number | null
    exit_slippage: number | null
    pnl_sol: number | null
    entry_reason: string
    exit_reason: string
    mode: string
    solscan_url: string | null
    exit_signature?: string | null
  }>
  events: Array<{
    id: number
    ts: string
    agent: string
    mint: string
    symbol: string
    message: string
  }>
}

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Błąd ${res.status}`
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* odpowiedź bez JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export function fetchSolanaStatus(): Promise<SolanaStatus> {
  return apiFetch(`${API_BASE}/solana/status`).then((res) => readJson<SolanaStatus>(res))
}

export function fetchSolanaJournal(): Promise<SolanaJournal> {
  return apiFetch(`${API_BASE}/solana/journal?limit=40`).then((res) => readJson<SolanaJournal>(res))
}

export function postSolanaArm(armed: boolean): Promise<SolanaStatus> {
  return apiFetch(`${API_BASE}/solana/arm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ armed }),
  }).then((res) => readJson<SolanaStatus>(res))
}

export function postSolanaControl(action: string): Promise<SolanaStatus> {
  return apiFetch(`${API_BASE}/solana/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  }).then((res) => readJson<SolanaStatus>(res))
}

export type TerminalPayload = {
  header: {
    title: string
    caption: string
    version: string
    mode: string
    pill: string
    running: boolean
    kill_switch: boolean
    worker_online: boolean
    equity_usd: number | null
    equity_sol: number | null
    sol_usd: number | null
    trades: number
    wins: number
    losses: number
    current_action: string | null
    tagline: string
    footer: string
    require_panel_arm?: boolean
    lock_reason?: string
  }
  agents: Array<{
    id: string
    name: string
    role: string
    rule: string
    color: string
    status_line: string
    badge: string
    health: string
    health_detail: string
    lessons: number
    lesson_line: string
    active: boolean
  }>
  online: number
  flow: {
    chips: Array<{ mint?: string; symbol?: string; metric?: string; state?: string }>
    checked_count: number
    sparkline: Array<{ ts: string; price: number }>
  }
  tiles: {
    filtered: number
    skipped: number
    last_size: { pct: number | null; sol: number | null; usd: number | null } | null
    logger_line: number | null
    last_close_pnl_usd: number | null
  }
  trade: {
    state: string
    symbol: string
    side: string
    live_pct: number | null
    entry: number | null
    exit_label: string | null
    slip: number | null
    size_pct: number | null
    reason: string
    exit_reason: string | null
  } | null
  tail: Array<{ id: number; time: string; kind: string; symbol: string; text: string; reason: string; pnl_usd: number | null; fill_source: string | null; lesson: boolean }>
  result: {
    label: string
    start_equity_usd: number | null
    now_equity_usd: number | null
    start_equity_sol: number
    now_equity_sol: number
    w: number
    l: number
    footer: string
  }
  log: Array<{ id: number; time: string; kind: string; symbol: string; reason: string; right: string | number | null; pnl_usd: number | null; lesson: boolean; fill_source: string | null }>
  lessons: { active: number; shadow: number; retired: number; llm: boolean; note: string | null }
  missing: Record<string, string>
  lines: number
  settings: Record<string, number | string>
  desk: { armed: boolean; running: boolean; kill_switch: boolean }
}

export function fetchSolanaTerminal(): Promise<TerminalPayload> {
  return apiFetch(`${API_BASE}/solana/terminal`).then((res) => readJson<TerminalPayload>(res))
}

export function fetchSolanaDecisions(beforeId: number): Promise<{ decisions: TerminalPayload['log'] }> {
  return apiFetch(`${API_BASE}/solana/decisions?before_id=${beforeId}&limit=50`).then((res) => readJson(res))
}

export function fetchSolanaLessons(agent = ''): Promise<{ lessons: Array<Record<string, unknown>> }> {
  const query = agent ? `?agent=${encodeURIComponent(agent)}` : ''
  return apiFetch(`${API_BASE}/solana/lessons${query}`).then((res) => readJson(res))
}

export function postSolanaSelfTest(): Promise<Record<string, unknown>> {
  return apiFetch(`${API_BASE}/solana/selftest`, { method: 'POST' }).then((res) => readJson(res))
}

export function fetchSolanaSelfTest(): Promise<Record<string, unknown>> {
  return apiFetch(`${API_BASE}/solana/selftest/last`).then((res) => readJson(res))
}

export function postSolanaSettings(patch: Record<string, number | string>): Promise<SolanaStatus> {
  return apiFetch(`${API_BASE}/solana/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  }).then((res) => readJson<SolanaStatus>(res))
}

export const solanaCsvUrl = `${API_BASE}/solana/trades.csv`
