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

export function postSolanaSettings(patch: Record<string, number>): Promise<SolanaStatus> {
  return apiFetch(`${API_BASE}/solana/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  }).then((res) => readJson<SolanaStatus>(res))
}

export const solanaCsvUrl = `${API_BASE}/solana/trades.csv`
