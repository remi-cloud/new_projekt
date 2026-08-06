import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAgentsReport, triggerScan } from '../api'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { positionPath } from '../lib/routes'
import type { AgentScoutInfo, AgentsReport, AgentVerdictInfo } from '../types'

function scoutShortLabel(label: string, id: string): string {
  const cleaned = label
    .replace(/^LONG\s*·\s*/i, '')
    .replace(/^SHORT\s*·\s*/i, '')
    .trim()
  if (cleaned) return cleaned
  const tail = id.split('.').pop() || id
  return tail.replace(/_/g, ' ')
}

function ConfidenceBar({ value, tone }: { value: number; tone: 'long' | 'short' }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div className={`sing-conf ${tone}`} aria-hidden>
      <span style={{ width: `${pct}%` }} />
    </div>
  )
}

function ScoutChip({ scout, tone }: { scout: AgentScoutInfo; tone: 'long' | 'short' }) {
  return (
    <div className={`sing-scout-chip ${tone}`}>
      <div className="sing-scout-chip-top">
        <strong>{scoutShortLabel(scout.label, scout.id)}</strong>
        <em>{scout.symbols}</em>
      </div>
      <div className="sing-scout-meter" aria-hidden>
        <span style={{ width: `${Math.min(100, (scout.symbols / 120) * 100)}%` }} />
      </div>
    </div>
  )
}

function VerdictTile({
  verdict,
  tone,
}: {
  verdict: AgentVerdictInfo
  tone: 'long' | 'short'
}) {
  const side = tone === 'long' ? 'LONG' : 'SHORT'
  return (
    <Link to={positionPath(verdict.symbol)} className={`sing-verdict ${tone} tap-target`}>
      <div className="sing-verdict-head">
        <div>
          <strong className="sing-verdict-sym">{verdict.symbol}</strong>
          {verdict.name && <span className="sing-verdict-name">{verdict.name}</span>}
        </div>
        <div className="sing-verdict-score">
          <em>{verdict.confidence.toFixed(0)}</em>
          <span>%</span>
        </div>
      </div>
      <ConfidenceBar value={verdict.confidence} tone={tone} />
      <div className="sing-verdict-meta">
        <span className={`sing-side-pill ${tone}`}>{side}</span>
        {(verdict.scout_ids ?? []).slice(0, 2).map((id) => (
          <span key={id} className="sing-scout-pill">
            {id.split('.').pop()}
          </span>
        ))}
      </div>
    </Link>
  )
}

function MergeBoard({ stats, lastScan }: { stats?: Record<string, unknown> | null; lastScan?: string | null }) {
  const rows = useMemo(() => {
    if (!stats) return []
    const order = [
      ['quotes', 'Kwoty'],
      ['long_scout_findings', 'Findings LONG'],
      ['short_scout_findings', 'Findings SHORT'],
      ['long_accepted', 'Accepted LONG'],
      ['short_accepted', 'Accepted SHORT'],
      ['merged', 'Merged'],
      ['merged_long', 'Torpeda LONG'],
      ['merged_short', 'Torpeda SHORT'],
      ['whale_symbols', 'Whale'],
    ] as const
    return order
      .filter(([key]) => stats[key] != null)
      .map(([key, label]) => ({
        key,
        label,
        value: Number(stats[key]) || 0,
      }))
  }, [stats])

  const max = Math.max(1, ...rows.map((r) => r.value))

  return (
    <section className="sing-merge">
      <div className="sing-merge-head">
        <div>
          <span className="sing-kicker">Final developer</span>
          <h3>Merge → Superokazje</h3>
          <p>
            LONG i SHORT 1:1, deduplikacja symboli, torpeda do sygnałów KUP · SPRZEDAJ.
          </p>
        </div>
        <time className="sing-scan-time">
          {lastScan ? new Date(lastScan).toLocaleString('pl-PL') : 'Brak skanu'}
        </time>
      </div>
      <div className="sing-merge-bars">
        {rows.map((row) => (
          <div key={row.key} className="sing-merge-row">
            <div className="sing-merge-label">
              <span>{row.label}</span>
              <strong>{row.value}</strong>
            </div>
            <div className="sing-merge-track" aria-hidden>
              <span style={{ width: `${(row.value / max) * 100}%` }} />
            </div>
          </div>
        ))}
        {rows.length === 0 && <p className="sing-empty">Brak statystyk — odpal Singularity.</p>}
      </div>
    </section>
  )
}

export default function AgentsPage() {
  const [data, setData] = useState<AgentsReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setError(null)
      const report = await fetchAgentsReport()
      setData(report)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się połączyć z Singularity')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const run = async () => {
    setBusy(true)
    try {
      await triggerScan()
      const report = await fetchAgentsReport(true)
      setData(report)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingState message="Budzenie Singularity…" />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  const longScouts = data.long_scouts ?? []
  const shortScouts = data.short_scouts ?? []
  const longVerdicts = (data.long_verdicts ?? []).slice(0, 12)
  const shortVerdicts = (data.short_verdicts ?? []).slice(0, 12)
  const longN = data.opportunities?.long ?? longVerdicts.length
  const shortN = data.opportunities?.short ?? shortVerdicts.length

  return (
    <div className="singularity-page institutional-page">
      <header className="sing-hero">
        <div className="sing-hero-copy">
          <span className="sing-kicker">Pipeline · multi-agent</span>
          <h2 className="page-headline">Singularity</h2>
          <p className="page-lead">
            Globalny radar scoutów, filtr specjalistów i finalny merge do Superokazji.
          </p>
        </div>
        <button className={`sing-run-btn tap-target${busy ? ' is-busy' : ''}`} type="button" disabled={busy} onClick={run}>
          <span className="sing-run-pulse" aria-hidden />
          {busy ? 'Liczy…' : 'Odpal Singularity'}
        </button>
      </header>

      <ol className="sing-pipeline" aria-label="Pipeline Singularity">
        <li className="sing-pipe-stage">
          <span className="sing-pipe-n">01</span>
          <strong>Scouts</strong>
          <em>
            {longScouts.length} LONG · {shortScouts.length} SHORT
          </em>
        </li>
        <li className="sing-pipe-link" aria-hidden />
        <li className="sing-pipe-stage">
          <span className="sing-pipe-n">02</span>
          <strong>Specjaliści</strong>
          <em>filtr confidence</em>
        </li>
        <li className="sing-pipe-link" aria-hidden />
        <li className="sing-pipe-stage is-hot">
          <span className="sing-pipe-n">03</span>
          <strong>Merge</strong>
          <em>
            {longN}↑ · {shortN}↓
          </em>
        </li>
      </ol>

      <div className="sing-meters" aria-label="Statystyki pipeline">
        <div className="sing-meter long">
          <span>Scout LONG</span>
          <strong>{data.counts?.long_scouts ?? longScouts.length}</strong>
        </div>
        <div className="sing-meter short">
          <span>Scout SHORT</span>
          <strong>{data.counts?.short_scouts ?? shortScouts.length}</strong>
        </div>
        <div className="sing-meter long">
          <span>Werdykty LONG</span>
          <strong>{longN}</strong>
        </div>
        <div className="sing-meter short">
          <span>Werdykty SHORT</span>
          <strong>{shortN}</strong>
        </div>
      </div>

      <div className="sing-rails">
        <section className="sing-rail long" aria-labelledby="sing-long-title">
          <header className="sing-rail-head">
            <h3 id="sing-long-title">Tor LONG</h3>
            <span>{longVerdicts.length} sygnałów</span>
          </header>
          <div className="sing-scout-row">
            {longScouts.map((s) => (
              <ScoutChip key={s.id} scout={s} tone="long" />
            ))}
          </div>
          <div className="sing-verdict-grid">
            {longVerdicts.map((v) => (
              <VerdictTile key={v.symbol} verdict={v} tone="long" />
            ))}
            {longVerdicts.length === 0 && <p className="sing-empty">Brak LONG — odpal Singularity.</p>}
          </div>
        </section>

        <section className="sing-rail short" aria-labelledby="sing-short-title">
          <header className="sing-rail-head">
            <h3 id="sing-short-title">Tor SHORT</h3>
            <span>{shortVerdicts.length} sygnałów</span>
          </header>
          <div className="sing-scout-row">
            {shortScouts.map((s) => (
              <ScoutChip key={s.id} scout={s} tone="short" />
            ))}
          </div>
          <div className="sing-verdict-grid">
            {shortVerdicts.map((v) => (
              <VerdictTile key={v.symbol} verdict={v} tone="short" />
            ))}
            {shortVerdicts.length === 0 && <p className="sing-empty">Brak SHORT — odpal Singularity.</p>}
          </div>
        </section>
      </div>

      <MergeBoard stats={data.last_stats} lastScan={data.last_scan_at} />

      <div className="sing-footer-link">
        <Link to="/superokazje" className="btn tap-target">
          Otwórz Superokazje →
        </Link>
      </div>
    </div>
  )
}
