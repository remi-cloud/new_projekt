import { useCallback, useEffect, useState } from 'react'
import { fetchAgentsReport, triggerScan } from '../api'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { AgentsReport } from '../types'

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

  if (loading) return <LoadingState message="Budzenie Singularity…" />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  const longScouts = data.long_scouts ?? []
  const shortScouts = data.short_scouts ?? []

  return (
    <div className="page agents-page singularity-page">
      <div className="page-header">
        <div>
          <p className="singularity-eyebrow">Moduł AI</p>
          <h1>Singularity</h1>
          <p className="page-lead">
            {longScouts.length} scoutów LONG + {shortScouts.length} scoutów SHORT globalnie →
            specjaliści AI LONG/SHORT → orchestrator. Tu zbiegają się wszystkie wnioski.
          </p>
        </div>
        <div className="page-actions">
          <button
            className="btn btn-primary"
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await triggerScan()
                await load()
              } finally {
                setBusy(false)
              }
            }}
          >
            {busy ? 'Singularity liczy…' : 'Odpal Singularity'}
          </button>
        </div>
      </div>

      <div className="super-stats">
        <div className="home-stat">
          <strong className="pos">{data.counts?.long_scouts ?? 0}</strong>
          <span>scout LONG</span>
        </div>
        <div className="home-stat">
          <strong className="neg">{data.counts?.short_scouts ?? 0}</strong>
          <span>scout SHORT</span>
        </div>
        <div className="home-stat">
          <strong>{data.opportunities?.long ?? 0}</strong>
          <span>werdykty LONG</span>
        </div>
        <div className="home-stat">
          <strong>{data.opportunities?.short ?? 0}</strong>
          <span>werdykty SHORT</span>
        </div>
      </div>

      <div className="agents-pipeline">
        <div className="agents-pipe-step">1 · Scouts</div>
        <div className="agents-pipe-arrow">→</div>
        <div className="agents-pipe-step">2 · Specjaliści</div>
        <div className="agents-pipe-arrow">→</div>
        <div className="agents-pipe-step hot">3 · Singularity</div>
      </div>

      <div className="agents-grid">
        <section className="agents-col long">
          <h2>Scoutowie LONG (świat)</h2>
          <ul className="agent-roster">
            {longScouts.map((s) => (
              <li key={s.id}>
                <strong>{s.label}</strong>
                <span>
                  {s.id} · {s.symbols} symboli
                </span>
              </li>
            ))}
          </ul>
          <h3>Specjalista LONG</h3>
          <ul className="agent-verdicts">
            {(data.long_verdicts ?? []).slice(0, 12).map((v) => (
              <li key={v.symbol}>
                <div className="agent-verdict-top">
                  <strong>{v.symbol}</strong>
                  <em>{v.confidence.toFixed(0)}%</em>
                </div>
                <p>{v.summary}</p>
                <span className="cell-sub">{v.scout_ids.join(', ')}</span>
              </li>
            ))}
            {(data.long_verdicts ?? []).length === 0 && (
              <li className="empty">Brak zaakceptowanych LONG — odpal Singularity.</li>
            )}
          </ul>
        </section>

        <section className="agents-col short">
          <h2>Scoutowie SHORT (świat)</h2>
          <ul className="agent-roster">
            {shortScouts.map((s) => (
              <li key={s.id}>
                <strong>{s.label}</strong>
                <span>
                  {s.id} · {s.symbols} symboli
                </span>
              </li>
            ))}
          </ul>
          <h3>Specjalista SHORT</h3>
          <ul className="agent-verdicts">
            {(data.short_verdicts ?? []).slice(0, 12).map((v) => (
              <li key={v.symbol}>
                <div className="agent-verdict-top">
                  <strong>{v.symbol}</strong>
                  <em>{v.confidence.toFixed(0)}%</em>
                </div>
                <p>{v.summary}</p>
                <span className="cell-sub">{v.scout_ids.join(', ')}</span>
              </li>
            ))}
            {(data.short_verdicts ?? []).length === 0 && (
              <li className="empty">Brak zaakceptowanych SHORT — odpal Singularity.</li>
            )}
          </ul>
        </section>
      </div>

      <section className="info-block">
        <h3>Singularity · Final Developer</h3>
        <p>
          Scala werdykty LONG i SHORT 1:1, deduplikuje symbole i przekazuje torpedę do Superokazji /
          sygnałów KUP·SPRZEDAJ. Ostatni skan:{' '}
          <strong>
            {data.last_scan_at ? new Date(data.last_scan_at).toLocaleString('pl-PL') : '—'}
          </strong>
        </p>
        {data.last_stats && (
          <pre className="agents-stats">{JSON.stringify(data.last_stats, null, 2)}</pre>
        )}
      </section>
    </div>
  )
}
