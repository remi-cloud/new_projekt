import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorState, Loading } from '../components/Loading'
import { deskSessionOpen } from '../lib/deskAuth'
import {
  fetchSolanaDecisions,
  fetchSolanaLessons,
  fetchSolanaSelfTest,
  fetchSolanaStatus,
  fetchSolanaTerminal,
  postSolanaArm,
  postSolanaControl,
  postSolanaSelfTest,
  postSolanaSettings,
  solanaCsvUrl,
  type SolanaStatus,
  type TerminalPayload,
} from '../lib/solanaDeskApi'
import { API_BASE } from '../lib/sameOrigin'
import '../styles/solana-desk.css'

const ICONS: Record<string, string> = {
  scanner: '▣',
  rug_check: '⚠',
  sizer: '◆',
  executor: '▶',
  logger: '✎',
  equity: '◉',
  you: '',
}

function osloClock(date: Date): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Oslo',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

function money(value: number): string {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function signedMoney(value: number): string {
  const body = money(Math.abs(value))
  return value > 0 ? `+${body}` : value < 0 ? `-${body.replace('-', '')}` : body
}

function missingText(missing: Record<string, string>, key: string, fallback: string): string {
  return `— ${missing[key] || fallback}`
}

function CountUp({ value, format }: { value: number | null; format: (n: number) => string }) {
  const [shown, setShown] = useState(value ?? 0)
  const from = useRef(value ?? 0)
  useEffect(() => {
    if (value == null) return
    const start = from.current
    const began = performance.now()
    let frame = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - began) / 420)
      const next = start + (value - start) * t
      setShown(next)
      if (t < 1) frame = requestAnimationFrame(step)
      else from.current = value
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [value])
  if (value == null) return <>{'—'}</>
  return <>{format(shown)}</>
}

export function SolanaDeskPage() {
  const [terminal, setTerminal] = useState<TerminalPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [clock, setClock] = useState(() => osloClock(new Date()))
  const [offline, setOffline] = useState(false)
  const [desk, setDesk] = useState(false)
  const [openControls, setOpenControls] = useState(false)
  const [status, setStatus] = useState<SolanaStatus | null>(null)
  const [form, setForm] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState('')
  const [debug, setDebug] = useState(false)
  const [lessonAgent, setLessonAgent] = useState<string | null>(null)
  const [lessons, setLessons] = useState<Array<Record<string, unknown>>>([])
  const [selftest, setSelftest] = useState<Record<string, unknown> | null>(null)
  const [extraLog, setExtraLog] = useState<TerminalPayload['log']>([])
  const logRef = useRef<HTMLDivElement>(null)
  const readKey = 'solana-desk-last-read'

  useEffect(() => {
    const id = window.setInterval(() => setClock(osloClock(new Date())), 1000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    let alive = true
    const sync = () => {
      void deskSessionOpen().then((open) => {
        if (alive) setDesk(open)
      })
    }
    sync()
    window.addEventListener('desk-auth', sync)
    return () => {
      alive = false
      window.removeEventListener('desk-auth', sync)
    }
  }, [])

  useEffect(() => {
    let alive = true
    let poll = 0
    let source: EventSource | null = null
    const apply = (payload: TerminalPayload) => {
      if (alive) setTerminal(payload)
    }
    const startPoll = () => {
      if (poll) return
      poll = window.setInterval(() => {
        void fetchSolanaTerminal().then(apply).catch(() => undefined)
      }, 3000)
    }
    void fetchSolanaTerminal()
      .then((payload) => {
        apply(payload)
        setError(null)
      })
      .catch((err: unknown) => {
        if (alive) setError(err instanceof Error ? err.message : 'Terminal unavailable')
      })
    if (typeof EventSource !== 'undefined') {
      source = new EventSource(`${API_BASE}/solana/stream`)
      source.addEventListener('snapshot', (event) => {
        setOffline(false)
        apply(JSON.parse((event as MessageEvent).data) as TerminalPayload)
      })
      source.onerror = () => {
        setOffline(true)
        startPoll()
      }
    } else {
      setOffline(true)
      startPoll()
    }
    return () => {
      alive = false
      source?.close()
      if (poll) window.clearInterval(poll)
    }
  }, [])

  useEffect(() => {
    if (!logRef.current) return
    logRef.current.scrollTop = logRef.current.scrollHeight
  }, [terminal?.lines])

  const unread = useMemo(() => {
    const lines = terminal?.lines ?? 0
    const seen = Number(localStorage.getItem(readKey) || 0)
    return Math.max(0, lines - seen)
  }, [terminal?.lines])

  if (!terminal && !error) return <Loading message="Ładuję Solana Desk…" />
  if (!terminal && error) return <ErrorState message={error} onRetry={() => window.location.reload()} />
  if (!terminal) return null

  const header = terminal.header
  const dotClass = header.kill_switch || !header.worker_online ? 'bad' : header.running ? '' : 'stop'
  const runningWord = header.kill_switch ? 'kill' : header.running ? 'running' : 'stopped'
  const activeName = (header.current_action || '').split('·')[0]?.trim().toLowerCase()
  const logRows = [...extraLog, ...terminal.log]
  const newest = logRows[logRows.length - 1]?.id
  const startUsd = terminal.result.start_equity_usd
  const nowUsd = terminal.result.now_equity_usd
  const delta = startUsd != null && nowUsd != null && startUsd !== 0 ? (nowUsd - startUsd) / Math.abs(startUsd) : 0

  const loadOlder = () => {
    const oldest = logRows[0]?.id
    if (!oldest) return
    void fetchSolanaDecisions(oldest).then((body) => {
      const older = (body.decisions || []).map((row) => ({
        id: Number(row.id),
        time: String((row as { ts?: string }).ts || '').slice(11, 16),
        kind: String(row.kind),
        symbol: String(row.symbol || ''),
        reason: String(row.reason || ''),
        right: '',
        pnl_usd: row.pnl_usd ?? null,
        lesson: String(row.reason || '').includes('lesson #'),
        fill_source: row.fill_source ?? null,
      }))
      setExtraLog((current) => [...older.reverse(), ...current])
    })
  }

  const openLessons = (agent: string) => {
    setLessonAgent(agent)
    void fetchSolanaLessons(agent).then((body) => setLessons(body.lessons || []))
  }

  const loadControls = () => {
    setOpenControls(true)
    void fetchSolanaStatus().then((next) => {
      setStatus(next)
      const initial: Record<string, string> = {}
      for (const [key, value] of Object.entries(next.settings || {})) initial[key] = String(value)
      setForm(initial)
    })
    void fetchSolanaSelfTest().then(setSelftest).catch(() => undefined)
  }

  const command = async (action: string) => {
    setNotice('')
    try {
      setStatus(await postSolanaControl(action))
      setNotice('Zapisane.')
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Komenda odrzucona.')
    }
  }

  const onSave = async (event: FormEvent) => {
    event.preventDefault()
    const patch: Record<string, number | string> = {}
    for (const [key, value] of Object.entries(form)) {
      if (value === '') continue
      if (key === 'session_start' || key === 'session_end') {
        patch[key] = value
        continue
      }
      const number = Number(value)
      if (!Number.isNaN(number)) patch[key] = number
    }
    try {
      setStatus(await postSolanaSettings(patch))
      setNotice('Ustawienia zapisane.')
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Nie zapisano.')
    }
  }

  const runSelfTest = async () => {
    setNotice('')
    try {
      setSelftest(await postSolanaSelfTest())
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Self-test odrzucony.')
    }
  }

  return (
    <div className="page solana-page">
      <section className="gbt" data-testid="gbt-terminal">
        <div className="gbt-caption">
          <span className="gbt-dots" aria-hidden="true"><i /><i /><i /></span>
          <p>{header.caption}</p>
          <span className={header.mode === 'real' ? 'gbt-pill real' : 'gbt-pill'} data-testid="gbt-mode">{header.pill}</span>
        </div>
        <header className="gbt-head">
          <div className="gbt-avatar" aria-hidden="true"><b /></div>
          <div>
            <div className="gbt-title">
              <strong>Grok Bot</strong>
              <span>Terminal</span>
              <em className="gbt-version">{header.version}</em>
            </div>
            <p className="gbt-status">
              <span className={`dot ${dotClass}`}>●</span> {runningWord} · <time data-testid="gbt-clock">{clock}</time>
              {offline ? <span className="gbt-offline"> · stream offline · retrying</span> : null}
            </p>
            {header.current_action ? <span className="gbt-action">{header.current_action}</span> : null}
            <p className="gbt-tag">{header.tagline}</p>
          </div>
          <div className="gbt-stats" data-testid="gbt-balance">
            <div>
              <strong>{header.equity_usd == null ? missingText(terminal.missing, 'equity_usd', 'no data (sol price down)') : <CountUp value={header.equity_usd} format={money} />}</strong>
              <small>balance</small>
              <span className="gbt-sol">{header.equity_sol == null ? '' : `${header.equity_sol.toFixed(4)} SOL`}</span>
            </div>
            <div>
              <strong><CountUp value={header.trades} format={(n) => String(Math.round(n))} /></strong>
              <small>trades</small>
            </div>
            <div>
              <strong className="pos"><CountUp value={header.wins} format={(n) => String(Math.round(n))} /></strong>
              <small>wins</small>
            </div>
            <div>
              <strong className={header.losses ? 'neg' : 'zero'}><CountUp value={header.losses} format={(n) => String(Math.round(n))} /></strong>
              <small>losses</small>
            </div>
          </div>
        </header>

        <div className="gbt-grid">
          <aside>
            <div className="gbt-col-head"><span>AGENTS</span><span>{terminal.online} online</span></div>
            <div className="gbt-agents">
              {terminal.agents.map((agent) => {
                const hot = activeName.includes(agent.name.toLowerCase()) || (agent.id === 'you' && false)
                return (
                  <article key={agent.id} className={hot ? 'gbt-card active' : 'gbt-card'} style={{ ['--agent' as string]: agent.color }}>
                    <div className="gbt-card-top">
                      {agent.id === 'you' ? <span className="gbt-you-icon"><b /></span> : <span className="gbt-ico">{ICONS[agent.id]}</span>}
                      <h3>{agent.name}</h3>
                      <span className={`gbt-badge ${agent.badge === 'IDLE' ? '' : 'on'} ${agent.badge === 'DOWN' ? 'down' : ''}`} title={agent.health_detail}>
                        <i className={`gbt-health ${agent.health}`} />
                        {agent.badge}
                      </span>
                    </div>
                    <p className="gbt-role">{agent.role}</p>
                    <p className="gbt-rule">{agent.rule}</p>
                    <p className="gbt-live">{agent.id === 'you' ? `${unread} lines to read` : agent.status_line}</p>
                    {agent.id !== 'you' ? (
                      <button type="button" className="gbt-lessons" onClick={() => openLessons(agent.id)}>{agent.lesson_line || `lessons ${agent.lessons}`}</button>
                    ) : (
                      <button
                        type="button"
                        className="gbt-lessons"
                        onClick={() => localStorage.setItem(readKey, String(terminal.lines))}
                      >
                        mark read
                      </button>
                    )}
                  </article>
                )
              })}
            </div>
          </aside>

          <div>
            <div className="gbt-flow-head">
              <span>LIVE FLOW · SCAN → CHECK → SIZE → EXEC → LOG</span>
              <span>checked {terminal.flow.checked_count}</span>
            </div>
            <div className="gbt-chips">
              {terminal.flow.chips.length === 0 ? <p className="gbt-foot">— no data (scanner idle)</p> : null}
              {terminal.flow.chips.map((chip) => (
                <article key={chip.mint || chip.symbol} className={`gbt-chip ${chip.state || 'queued'}`}>
                  <i className="gbt-dot" />
                  <b>${chip.symbol}</b>
                  <small>{chip.metric}</small>
                </article>
              ))}
            </div>
            <div className="gbt-graph" aria-hidden="true">
              <svg viewBox="0 0 640 160">
                <path d="M80 40 H200 M150 70 H250 M220 40 H300 M300 40 H430" fill="none" stroke="#55535c" strokeDasharray="4 4" />
                <path d="M250 110 H470" fill="none" stroke="#55535c" strokeDasharray="4 4" />
                <text x="300" y="102" fill="#9a98a3" fontSize="11">pass → size → enter</text>
              </svg>
              {header.current_action?.includes('FILTERED') ? <div className="gbt-stamp">FILTERED</div> : null}
              <div className="gbt-spark">
                <Spark ticks={terminal.flow.sparkline} symbol={terminal.trade?.symbol} live={terminal.trade?.live_pct ?? null} missing={terminal.missing.sparkline} />
              </div>
              <div className="gbt-node rug"><i>⚠</i>RUG CHECK<br />{terminal.agents.find((a) => a.id === 'rug_check')?.badge === 'FILTER' ? `FILTER $${terminal.trade?.symbol || ''}` : terminal.agents.find((a) => a.id === 'rug_check')?.status_line}</div>
              <div className="gbt-node exec"><i>▶</i>EXECUTOR<br />{terminal.agents.find((a) => a.id === 'executor')?.status_line}</div>
            </div>
            <div className="gbt-tiles">
              <article className="gbt-tile"><span>FILTERED</span><b>{terminal.tiles.filtered}</b><small>+ {terminal.tiles.skipped} skipped</small></article>
              <article className="gbt-tile">
                <span>SIZER</span>
                <b>{terminal.tiles.last_size?.pct != null ? `${Math.round(terminal.tiles.last_size.pct * 100)}% eq` : '—'}</b>
                <small>{terminal.tiles.last_size ? `${terminal.tiles.last_size.sol?.toFixed(4) ?? '—'} SOL` : 'no size yet'}</small>
              </article>
              <article className="gbt-tile"><span>LOGGER</span><b>{terminal.tiles.logger_line == null ? '—' : `line #${terminal.tiles.logger_line}`}</b><small>each with a reason</small></article>
              <article className="gbt-tile">
                <span>EQUITY</span>
                <b className={(terminal.tiles.last_close_pnl_usd || 0) >= 0 ? 'pos' : 'neg'}>
                  {terminal.tiles.last_close_pnl_usd == null ? '—' : signedMoney(terminal.tiles.last_close_pnl_usd)}
                </b>
                <small>{terminal.tiles.last_close_pnl_usd == null ? 'no close yet' : 'last close'}</small>
              </article>
            </div>

            <div className="gbt-split">
              <article className="gbt-trade">
                <div className="gbt-card-head"><span>TRADE · ENTRY vs EXIT</span><span>{terminal.trade?.state || '—'}</span></div>
                {terminal.trade ? (
                  <>
                    <div className="gbt-symbol">
                      <strong>${terminal.trade.symbol}</strong>
                      <em className="gbt-long">{terminal.trade.side}</em>
                      <span className={terminal.trade.live_pct != null && terminal.trade.live_pct < 0 ? 'gbt-livepct neg' : 'gbt-livepct pos'}>
                        {terminal.trade.live_pct == null ? '—' : `${terminal.trade.live_pct.toFixed(1)}% live`}
                      </span>
                    </div>
                    <div className="gbt-kv">
                      <span>entry</span><b>{terminal.trade.entry ?? '—'}</b>
                      <span>exit</span><b>{terminal.trade.exit_label || 'open'}</b>
                      <span>slip</span><b>{terminal.trade.slip == null ? '—' : `${(terminal.trade.slip * 100).toFixed(2)}%`}</b>
                      <span>size</span><b>{terminal.trade.size_pct == null ? '—' : `${Math.round(terminal.trade.size_pct * 100)}% of equity`}</b>
                      <span>reason</span><b>{terminal.trade.reason}</b>
                      <span>exit</span><b>{terminal.trade.exit_reason || '—'}</b>
                    </div>
                  </>
                ) : <p>{missingText(terminal.missing, 'trade', 'no close yet')}</p>}
              </article>
              <article className="gbt-tail">
                <div className="gbt-card-head">
                  <span>$ tail -f night.log</span>
                  <span>{terminal.lines} lines <button type="button" onClick={() => setDebug((value) => !value)}>{debug ? 'debug on' : 'debug'}</button></span>
                </div>
                {(debug ? terminal.tail : terminal.tail.filter((line) => !['QUOTE', 'SEND', 'CONFIRM', 'RETRY'].includes(line.kind))).map((line) => (
                  <p key={line.id} className={`gbt-tail-line ${line.kind} ${(line.pnl_usd || 0) < 0 ? 'neg' : 'pos'}`}>
                    {line.time} {line.text}
                    {line.fill_source === 'model' ? <em className="gbt-model"> MODEL</em> : null}
                    {line.lesson ? <em> LESSON</em> : null}
                    <small>reason: {line.reason}</small>
                  </p>
                ))}
                <span className="gbt-cursor" />
              </article>
            </div>

            <article className="gbt-result">
              <div className="gbt-card-head"><span>RESULT · start vs now</span><span>{terminal.result.label}</span></div>
              <p>START ● {startUsd == null ? missingText(terminal.missing, 'equity_usd', 'no data (sol price down)') : money(startUsd)}</p>
              <div className={delta < 0 ? 'gbt-bar down' : 'gbt-bar'}><span style={{ ['--w' as string]: `${Math.min(100, Math.abs(delta) * 100)}%` }} /></div>
              <p>NOW ● {nowUsd == null ? '—' : money(nowUsd)}</p>
              <p><b className="pos">{terminal.result.w} W</b> / <b className="neg">{terminal.result.l} L</b></p>
              <p className="gbt-foot" data-testid="gbt-footer">{terminal.result.footer}</p>
            </article>

            <article className="gbt-log" ref={logRef} onScroll={(event) => {
              if (event.currentTarget.scrollTop < 8) loadOlder()
            }}>
              <div className="gbt-card-head">
                <span>LOG</span>
                <span><em className="gbt-struck">would you long this?</em> → reading the log</span>
              </div>
              <p className="gbt-foot">lessons {terminal.lessons.active} active · {terminal.lessons.shadow} shadow · {terminal.lessons.retired} retired{terminal.lessons.note ? ` · ${terminal.lessons.note}` : ''}</p>
              {logRows.map((row) => (
                <div key={`${row.id}-${row.time}`} className={row.id === newest ? 'gbt-log-row newest' : 'gbt-log-row'}>
                  <span>{row.time}</span>
                  <span className={`gbt-kind ${row.kind} ${(row.pnl_usd || 0) < 0 ? 'neg' : 'pos'}`}>{row.kind}{row.fill_source === 'model' ? ' MODEL' : ''}{row.lesson ? ' LESSON' : ''}</span>
                  <p>${row.symbol}<br /><small>reason: {row.reason}</small></p>
                  <b className={typeof row.right === 'number' && row.right < 0 ? 'neg' : 'pos'}>
                    {typeof row.right === 'number' ? signedMoney(row.right) : row.right || '—'}
                  </b>
                </div>
              ))}
            </article>
          </div>
        </div>

        {lessonAgent ? (
          <aside className="gbt-lessons-drawer">
            <div className="gbt-card-head"><span>lessons · {lessonAgent}</span><button type="button" onClick={() => setLessonAgent(null)}>close</button></div>
            {lessons.length === 0 ? <p>no lessons yet</p> : lessons.map((row) => (
              <p key={String(row.id)}>#{String(row.id)} {String(row.status)} · {String(row.lesson_text)} · applied {String(row.times_applied ?? 0)}</p>
            ))}
          </aside>
        ) : null}

        <div className="gbt-drawer">
          <button type="button" onClick={loadControls}>Sterowanie</button>
          {openControls ? (
            <div>
              {!desk ? <p className="gbt-foot">Gość tylko czyta. <Link to="/logowanie">Zaloguj biurko</Link>.</p> : null}
              <div className="gbt-controls">
                <button type="button" className="btn btn-primary" disabled={!desk} onClick={() => void command('start')}>Start</button>
                <button type="button" className="btn btn-ghost" disabled={!desk} onClick={() => void command('stop')}>Stop</button>
                <button type="button" className="btn btn-ghost" disabled={!desk} onClick={() => void command('kill')}>Wyłącznik awaryjny</button>
                <button type="button" className="btn btn-ghost" disabled={!desk || !status?.kill_switch} onClick={() => void command('clear_kill')}>Zdejmij wyłącznik</button>
                <button type="button" className="btn btn-ghost" disabled={!desk || !status} onClick={() => status && void postSolanaArm(!status.armed).then(setStatus)}>
                  {status?.armed ? 'Rozbrój handel realny' : 'Uzbrój handel realny'}
                </button>
                <a href={solanaCsvUrl}>Eksport CSV</a>
                <button type="button" disabled={!desk} onClick={() => void runSelfTest()}>Self-test</button>
              </div>
              <p className="gbt-foot">
                {header.require_panel_arm
                  ? 'Zamek panelu jest wymagany i schodzi po restarcie.'
                  : 'Zamek panelu jest opcjonalny. Handel realny idzie po SOLANA_REAL_TRADING, kluczu i RPC.'}
                {' '}{header.lock_reason}
              </p>
              <form className="gbt-form" onSubmit={(event) => void onSave(event)}>
                {['risk_per_trade_pct', 'min_size_pct', 'max_size_pct', 'max_slippage_pct', 'max_per_trade_sol', 'daily_loss_sol', 'stop_pct', 'min_reserve_sol', 'position_sol', 'session_start', 'session_end'].map((key) => (
                  <label key={key}>
                    {key === 'position_sol' ? 'position_sol (przestarzałe)' : key}
                    <input className="field-input" disabled={!desk} value={form[key] || ''} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />
                  </label>
                ))}
                <button className="btn btn-primary" type="submit" disabled={!desk}>Zapisz</button>
              </form>
              {notice ? <p className="gbt-foot">{notice}</p> : null}
              {selftest ? (
                <div className="gbt-selftest">
                  <strong>Self-test {String(selftest.ok)}</strong>
                  {Object.entries((selftest.agents as Record<string, { ok?: boolean; detail?: string }>) || {}).map(([name, row]) => (
                    <p key={name}>{name}: {row?.ok ? 'ok' : 'fail'} {row?.detail || ''}</p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

function Spark({ ticks, symbol, live, missing }: { ticks: Array<{ price: number }>; symbol?: string; live: number | null; missing?: string }) {
  if (!ticks.length) return <p className="gbt-foot">{symbol ? `$${symbol} live` : '—'} {missing ? `— ${missing}` : ''}</p>
  const prices = ticks.map((tick) => tick.price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const span = max - min || 1
  const d = prices.map((price, index) => {
    const x = (index / Math.max(1, prices.length - 1)) * 180
    const y = 40 - ((price - min) / span) * 36
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
  const tone = live != null && live < 0 ? '#ff5a6a' : '#3bfe49'
  return (
    <svg viewBox="0 0 180 48">
      <text x="0" y="10" fill="#9a98a3" fontSize="10">${symbol} live</text>
      <text x="120" y="10" fill={tone} fontSize="10">{live == null ? '' : `${live.toFixed(1)}%`}</text>
      <path d={d} fill="none" stroke={tone} strokeWidth="1.6" />
    </svg>
  )
}
