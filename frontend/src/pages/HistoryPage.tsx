import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchHistory } from '../api'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { formatSignal, signalDirection } from '../lib/labels'
import { positionPath } from '../lib/routes'
import { HistoryResponse } from '../types'

export default function HistoryPage() {
  const [data, setData] = useState<HistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await fetchHistory())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się pobrać historii')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) return <LoadingState message="Ładowanie historii sygnałów…" />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Historia skanów</h1>
          <p className="page-lead">
            Kliknij instrument, aby otworzyć pełną pozycję (bid/ask, poziomy, heatmapa).
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} type="button">
          Odśwież
        </button>
      </div>

      <h2 className="section-title">
        Zmiany sygnałów
        <span className="count">{data.changes.length}</span>
      </h2>
      {data.changes.length === 0 ? (
        <p className="empty">Brak wykrytych zmian — uruchom kilka skanów, aby zobaczyć historię.</p>
      ) : (
        <div className="assets-table-wrap">
          <table className="assets-table">
            <thead>
              <tr>
                <th>Czas</th>
                <th>Instrument</th>
                <th>Było</th>
                <th>Jest</th>
                <th>Pewność</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.changes.map((c) => (
                <tr key={c.id} className="row-link">
                  <td className="cell-sub">{new Date(c.created_at).toLocaleString('pl-PL')}</td>
                  <td>
                    <Link to={positionPath(c.symbol)} className="row-main-link">
                      <strong>{c.name}</strong>
                      <div className="cell-sub">{c.symbol}</div>
                    </Link>
                  </td>
                  <td>{c.previous_action ? formatSignal(c.previous_action) : '—'}</td>
                  <td>
                    <span className={`signal-tag signal-${signalDirection(c.new_action)}`}>
                      {formatSignal(c.new_action)}
                    </span>
                  </td>
                  <td className="price-cell">{c.new_confidence}%</td>
                  <td>
                    <Link to={positionPath(c.symbol)} className="btn btn-ghost btn-sm">
                      Otwórz
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="section-title">
        Log skanów
        <span className="count">{data.scans.length}</span>
      </h2>
      <div className="assets-table-wrap">
        <table className="assets-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Czas</th>
              <th>Okazje</th>
              <th>Zmiany</th>
            </tr>
          </thead>
          <tbody>
            {data.scans.map((s) => (
              <tr key={s.id}>
                <td className="price-cell">{s.id}</td>
                <td>{new Date(s.scanned_at).toLocaleString('pl-PL')}</td>
                <td>{s.opportunities_count}</td>
                <td>{s.changes_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
