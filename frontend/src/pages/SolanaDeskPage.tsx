import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorState, Loading } from '../components/Loading'
import { readDeskToken } from '../lib/deskAuth'
import {
  fetchSolanaJournal,
  fetchSolanaStatus,
  postSolanaArm,
  postSolanaControl,
  postSolanaSettings,
  solanaCsvUrl,
  type SolanaJournal,
  type SolanaStatus,
} from '../lib/solanaDeskApi'
import '../styles/solana-desk.css'

const AGENTS = [
  ['scout', 'Scout', 'Szuka nowych mintów na pump.fun i wzrostów na krzywej oraz Raydium.'],
  ['checker', 'Checker', 'Odrzuca mint z władzą mint/freeze, koncentracją, dev walletem albo luką w danych.'],
  ['sniper', 'Sniper', 'Wchodzi papierowo dopiero na kolejnej cenie, rozmiarem z ustawień.'],
  ['exit', 'Exit', 'Stop -6%, take-profit, trailing i time-stop. Luka zostaje luką.'],
] as const

function sol(value: number | null | undefined, digits = 4): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toFixed(digits)} SOL`
}

function usd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const abs = Math.abs(Number(value))
  const digits = abs > 0 && abs < 0.01 ? 8 : 4
  return `${Number(value).toFixed(digits)} USD`
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(1)}%`
}

function tone(value: number): string {
  if (value > 0) return 'solana-up'
  if (value < 0) return 'solana-down'
  return ''
}

export function SolanaDeskPage() {
  const [status, setStatus] = useState<SolanaStatus | null>(null)
  const [journal, setJournal] = useState<SolanaJournal>({ trades: [], events: [] })
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [desk, setDesk] = useState(() => readDeskToken().length > 0)
  const [form, setForm] = useState<Record<string, string>>({})
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const sync = () => setDesk(readDeskToken().length > 0)
    window.addEventListener('desk-auth', sync)
    return () => window.removeEventListener('desk-auth', sync)
  }, [])

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const [nextStatus, nextJournal] = await Promise.all([fetchSolanaStatus(), fetchSolanaJournal()])
        if (!alive) return
        setStatus(nextStatus)
        setJournal(nextJournal)
        setError(null)
        if (!ready) {
          const settings = nextStatus.settings || {}
          const initial: Record<string, string> = {}
          for (const [key, value] of Object.entries(settings)) initial[key] = String(value)
          setForm(initial)
          setReady(true)
        }
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : 'Nie udało się wczytać biurka.')
      }
    }
    void load()
    const timer = window.setInterval(() => void load(), 8000)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [ready])

  const command = async (action: string) => {
    setNotice('')
    try {
      const next = await postSolanaControl(action)
      setStatus(next)
      setNotice('Zapisane.')
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Komenda odrzucona.')
    }
  }

  const onSave = async (event: FormEvent) => {
    event.preventDefault()
    setNotice('')
    const patch: Record<string, number> = {}
    const lockedCapital = (status?.closed_trades ?? 0) > 0 || (status?.open_positions ?? 0) > 0
    for (const [key, value] of Object.entries(form)) {
      if (value === '' || key === 'starting_usd') continue
      if (lockedCapital && key === 'starting_sol') continue
      const number = Number(value)
      if (!Number.isNaN(number)) patch[key] = number
    }
    const usdBudget = Number(form.starting_usd || '')
    if (!lockedCapital && usdBudget >= 20 && usdBudget <= 50) patch.starting_usd = usdBudget
    try {
      const next = await postSolanaSettings(patch)
      setStatus(next)
      setNotice('Ustawienia zapisane.')
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Nie zapisano.')
    }
  }

  if (!status && !error) return <Loading message="Ładuję Solana Desk…" />
  if (!status && error) return <ErrorState message={error} onRetry={() => setReady(false)} />
  if (!status) return null

  const lockedCapital = status.closed_trades > 0 || status.open_positions > 0

  return (
    <div className="page solana-page">
      <header className="page-intro">
        <span className="page-eyebrow">Biurko · Solana</span>
        <h2 className="page-headline">Solana Desk</h2>
        <p className="page-lead">
          Cztery agenty handlują memecoinami z pump.fun na papierze, na żywych cenach.
          Żadne zlecenie nie idzie na łańcuch.
        </p>
      </header>

      <p className="solana-banner" role="status">
        Tryb papierowy. Handel realny jest wyłączony
        {status.wallet_configured ? ' (klucz portfela jest ustawiony, ale nic nie podpisujemy)' : ''}.{' '}
        {status.lock_reason}
      </p>

      <div className="solana-stats">
        <div className="mini-stat"><span>Saldo</span><strong>{sol(status.cash_sol)}</strong></div>
        <div className="mini-stat"><span>Kapitał</span><strong>{sol(status.equity_sol)}</strong></div>
        <div className="mini-stat">
          <span>PnL po opłatach</span>
          <strong className={tone(status.net_pnl_sol)}>{sol(status.net_pnl_sol)}</strong>
        </div>
        <div className="mini-stat"><span>Win rate</span><strong>{pct(status.win_rate)}</strong></div>
        <div className="mini-stat"><span>Transakcje</span><strong>{status.closed_trades}</strong></div>
        <div className="mini-stat"><span>Max drawdown</span><strong>{pct(status.max_drawdown)}</strong></div>
      </div>

      <p className="solana-note">
        {status.worker_online ? 'Worker tyka.' : 'Worker czeka na kolejny obieg.'}{' '}
        Ostatni obieg: {status.last_tick_at || 'jeszcze nie było'}. Kurs SOL: {usd(status.sol_usd)}.
        Opłaty łącznie: {sol(status.fees_sol, 6)}.
        {status.last_error ? ` Źródło: ${status.last_error}.` : ''}
      </p>

      <div className="solana-agents">
        {AGENTS.map(([id, label, blurb]) => {
          const agent = status.agents?.[id] || {}
          const figure =
            id === 'scout' ? agent.seen ?? 0
            : id === 'checker' ? `${agent.passed ?? 0} / ${agent.rejected ?? 0}`
            : id === 'sniper' ? agent.entries ?? 0
            : agent.exits ?? 0
          return (
            <article key={id} className="solana-agent">
              <span>{label}</span>
              <strong>{figure}</strong>
              <p>{agent.note || blurb}</p>
            </article>
          )
        })}
      </div>

      <h3 className="solana-section">Pozycje</h3>
      {status.positions.length === 0 ? (
        <p className="empty">Brak otwartych pozycji papierowych.</p>
      ) : (
        <div className="solana-journal">
          {status.positions.map((row) => (
            <article key={row.mint} className="solana-row">
              <b>{row.symbol} · {row.status === 'pending' ? 'czeka na cenę' : 'otwarta'}</b>
              <span className="solana-mint">{row.mint}</span>
              <small>
                Wejście {usd(row.entry_price)} · teraz {usd(row.last_price)} · {sol(row.size_sol)} ·{' '}
                <em className={tone(row.unrealized_pnl_sol)}>{sol(row.unrealized_pnl_sol)}</em>
              </small>
            </article>
          ))}
        </div>
      )}

      <h3 className="solana-section">Na żywo</h3>
      {journal.events.length === 0 ? (
        <p className="empty">Agenty jeszcze nic nie zapisały.</p>
      ) : (
        <div className="solana-live">
          {journal.events.slice(0, 12).map((event) => (
            <article key={event.id} className="solana-row">
              <b>{event.agent} · {event.symbol || 'biurko'}</b>
              <small>{event.ts} UTC</small>
              <p>{event.message}</p>
            </article>
          ))}
        </div>
      )}

      <h3 className="solana-section">Dziennik</h3>
      <p>
        <a href={solanaCsvUrl}>Eksport CSV</a>
      </p>
      {journal.trades.length === 0 ? (
        <p className="empty">Dziennik jest pusty. Wejście zapisuje się po opóźnieniu jednego obiegu.</p>
      ) : (
        <div className="solana-journal">
          {journal.trades.map((trade) => (
            <article key={trade.id} className="solana-row">
              <b>{trade.symbol} · {trade.status === 'closed' ? 'zamknięta' : 'otwarta'}</b>
              <span className="solana-mint">{trade.mint}</span>
              <small>
                {trade.closed_at || trade.opened_at} UTC · wejście {usd(trade.entry_price)} · wyjście{' '}
                {usd(trade.exit_price)} · opłaty {sol((trade.entry_fee_sol || 0) + (trade.exit_fee_sol || 0), 6)}
                {' · '}poślizg {pct(trade.entry_slippage)} / {pct(trade.exit_slippage)}
                {' · '}
                <em className={tone(trade.pnl_sol || 0)}>{trade.pnl_sol == null ? 'otwarta' : sol(trade.pnl_sol)}</em>
              </small>
              <p>{trade.entry_reason}</p>
              {trade.exit_reason ? <p>{trade.exit_reason}</p> : null}
              {trade.solscan_url ? <a href={trade.solscan_url}>Solscan</a> : null}
            </article>
          ))}
        </div>
      )}

      <h3 className="solana-section">Raport dzienny</h3>
      {status.report ? (
        <article className="solana-report">
          <strong>{status.report.title}</strong>
          <p>
            PnL {sol(status.report.pnl_sol)} · opłaty {sol(status.report.fees_sol, 6)} · transakcje{' '}
            {status.report.closed_trades ?? 0} · win rate {pct(status.report.win_rate)} · drawdown{' '}
            {pct(status.report.max_drawdown)}
          </p>
          <p>{status.report.note}</p>
        </article>
      ) : (
        <p className="empty">Raport pojawi się po pierwszym obiegu.</p>
      )}

      <h3 className="solana-section">Sterowanie</h3>
      {!desk && (
        <p className="solana-note">
          Gość tylko czyta. <Link to="/logowanie">Zaloguj biurko</Link>, żeby uruchamiać, zatrzymywać i zmieniać limity.
        </p>
      )}
      <div className="solana-controls">
        <button type="button" className="btn btn-primary" disabled={!desk} onClick={() => void command('start')}>Start</button>
        <button type="button" className="btn btn-ghost" disabled={!desk} onClick={() => void command('stop')}>Stop</button>
        <button type="button" className="btn btn-ghost" disabled={!desk} onClick={() => void command('kill')}>Wyłącznik awaryjny</button>
        <button type="button" className="btn btn-ghost" disabled={!desk || !status.kill_switch} onClick={() => void command('clear_kill')}>
          Zdejmij wyłącznik
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!desk}
          onClick={() => void postSolanaArm(!status.armed).then(setStatus).catch((err: unknown) => setNotice(err instanceof Error ? err.message : 'Zamek odrzucony.'))}
        >
          {status.armed ? 'Rozbrój handel realny' : 'Uzbrój handel realny'}
        </button>
      </div>
      <p className="solana-note">
        Zamek realny: {status.armed ? 'uzbrojony' : 'rozbrojony'}. Po restarcie serwera sam schodzi.
        Trasa: Jupiter Swap API. Bez flagi, klucza, RPC i zamka nic nie wychodzi na łańcuch.
      </p>
      <form className="solana-form" onSubmit={(event) => void onSave(event)}>
        <label>
          Start SOL
          <input className="field-input" inputMode="decimal" disabled={!desk || lockedCapital} value={form.starting_sol || ''} onChange={(event) => setForm({ ...form, starting_sol: event.target.value })} />
        </label>
        <label>
          Albo 20–50 USD
          <input className="field-input" inputMode="decimal" disabled={!desk || lockedCapital} value={form.starting_usd || ''} onChange={(event) => setForm({ ...form, starting_usd: event.target.value })} />
        </label>
        <label>
          Rozmiar pozycji
          <input className="field-input" inputMode="decimal" disabled={!desk} value={form.position_sol || ''} onChange={(event) => setForm({ ...form, position_sol: event.target.value })} />
        </label>
        <label>
          Maks. na transakcję
          <input className="field-input" inputMode="decimal" disabled={!desk} value={form.max_per_trade_sol || ''} onChange={(event) => setForm({ ...form, max_per_trade_sol: event.target.value })} />
        </label>
        <label>
          Dzienny limit straty
          <input className="field-input" inputMode="decimal" disabled={!desk} value={form.daily_loss_sol || ''} onChange={(event) => setForm({ ...form, daily_loss_sol: event.target.value })} />
        </label>
        <label>
          Stop (ułamek)
          <input className="field-input" inputMode="decimal" disabled={!desk} value={form.stop_pct || ''} onChange={(event) => setForm({ ...form, stop_pct: event.target.value })} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={!desk}>Zapisz</button>
      </form>
      {notice ? <p className="solana-note">{notice}</p> : null}
      <p className="solana-note">
        Stan: {status.running ? 'pracuje' : 'zatrzymane'}
        {status.kill_switch ? ', wyłącznik awaryjny włączony' : ''}. Startowy kapitał to domyślnie 1 SOL.
        Mały rachunek: 20–50 USD, zanim padnie pierwsza transakcja.
      </p>
    </div>
  )
}
