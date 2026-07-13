import { useCallback, useEffect, useState } from 'react'
import { fetchDashboard, triggerScan } from './api'
import {
  AssetClass,
  AssetQuote,
  BitcoinCycleStatus,
  DashboardResponse,
  Opportunity,
  PresidentialCycleStatus,
  SignalAction,
} from './types'

const ASSET_LABELS: Record<AssetClass, string> = {
  crypto: 'Krypto',
  stock: 'Akcje',
  index: 'Indeksy',
  bond: 'Obligacje',
  commodity: 'Surowce',
  forex: 'Forex',
}

const SIGNAL_LABELS: Record<SignalAction, string> = {
  buy: 'Kupuj',
  sell: 'Sprzedaj',
  hold: 'Trzymaj',
  watch: 'Obserwuj',
}

const PHASE_LABELS: Record<string, string> = {
  bear: 'Spadkowa',
  accumulation: 'Akumulacja',
  bull: 'Wzrostowa',
  distribution: 'Dystrybucja',
  neutral: 'Neutralna',
  year_1: 'Rok 1',
  year_2: 'Rok 2',
  year_3: 'Rok 3',
  year_4: 'Rok 4',
}

function formatPrice(price: number, assetClass: AssetClass): string {
  if (assetClass === 'forex') return price.toFixed(4)
  if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (price >= 1) return price.toFixed(2)
  return price.toFixed(4)
}

function ChangeCell({ value }: { value: number | null }) {
  if (value === null) return <span className="change-neutral">—</span>
  const cls = value > 0 ? 'change-positive' : value < 0 ? 'change-negative' : 'change-neutral'
  return <span className={cls}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
}

function CycleCardBitcoin({ cycle }: { cycle: BitcoinCycleStatus }) {
  const progressClass = cycle.phase === 'bear' ? 'bear' : cycle.phase === 'bull' ? 'bull' : 'neutral'
  return (
    <div className="cycle-card bitcoin">
      <div className="cycle-card-header">
        <h2>Cykl Bitcoin (364 / 1064 dni)</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{SIGNAL_LABELS[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Ostatnie ATH</div>
          <div className="stat-value">${cycle.last_ath_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Cena bieżąca</div>
          <div className="stat-value">${cycle.current_price.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Dni od ATH</div>
          <div className="stat-value">{cycle.days_since_ath}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Faza</div>
          <div className="stat-value">{PHASE_LABELS[cycle.phase] ?? cycle.phase}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div
          className={`progress-fill ${progressClass}`}
          style={{ width: `${cycle.phase_progress_pct}%` }}
        />
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>
        Postęp fazy: {cycle.phase_progress_pct}% · Pozostało {cycle.days_remaining_in_phase} dni
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}

function CycleCardPresidential({ cycle }: { cycle: PresidentialCycleStatus }) {
  return (
    <div className="cycle-card presidential">
      <div className="cycle-card-header">
        <h2>Cykl prezydencki USA</h2>
        <span className={`signal-tag signal-${cycle.signal}`}>{SIGNAL_LABELS[cycle.signal]}</span>
      </div>
      <div className="cycle-stats">
        <div className="stat">
          <div className="stat-label">Prezydent</div>
          <div className="stat-value">{cycle.president}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Rok kadencji</div>
          <div className="stat-value">{PHASE_LABELS[cycle.current_year] ?? cycle.current_year}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Dzień roku</div>
          <div className="stat-value">{cycle.days_into_year}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Historyczny bias</div>
          <div className="stat-value" style={{ fontSize: '0.85rem' }}>{cycle.historical_bias.split('—')[0]}</div>
        </div>
      </div>
      <div className="progress-bar">
        <div
          className="progress-fill neutral"
          style={{ width: `${cycle.year_progress_pct}%` }}
        />
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>
        Postęp roku: {cycle.year_progress_pct}% · Pozostało {cycle.days_remaining_in_year} dni
      </div>
      <p className="cycle-rationale">{cycle.rationale}</p>
    </div>
  )
}

function OpportunityCard({ opp }: { opp: Opportunity }) {
  return (
    <div className="opp-card">
      <div className="opp-header">
        <div>
          <div className="opp-name">{opp.name}</div>
          <div className="opp-symbol">{opp.symbol}</div>
        </div>
        <span className={`signal-tag signal-${opp.action}`}>{SIGNAL_LABELS[opp.action]}</span>
      </div>
      <div className="confidence-bar">
        <div className="confidence-track">
          <div className="confidence-fill" style={{ width: `${opp.confidence}%` }} />
        </div>
        <span className="confidence-pct">{opp.confidence}%</span>
      </div>
      <div className="opp-meta">
        <span className={`tag ${opp.asset_class}`}>{ASSET_LABELS[opp.asset_class]}</span>
        <span className="tag">{opp.cycle_source === 'bitcoin_cycle' ? 'Cykl BTC' : 'Cykl prez.'}</span>
        <span className="tag">${formatPrice(opp.price, opp.asset_class)}</span>
      </div>
      <p className="opp-rationale">{opp.rationale}</p>
    </div>
  )
}

function AssetsTable({ assets }: { assets: AssetQuote[] }) {
  return (
    <div className="assets-table-wrap">
      <table className="assets-table">
        <thead>
          <tr>
            <th>Instrument</th>
            <th>Klasa</th>
            <th>Cena</th>
            <th>24h</th>
            <th>7d</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => (
            <tr key={a.symbol}>
              <td>
                <strong>{a.name}</strong>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {a.symbol}
                </div>
              </td>
              <td><span className={`tag ${a.asset_class}`}>{ASSET_LABELS[a.asset_class]}</span></td>
              <td className="price-cell">${formatPrice(a.price, a.asset_class)}</td>
              <td><ChangeCell value={a.change_pct_24h} /></td>
              <td><ChangeCell value={a.change_pct_7d} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function App() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const dashboard = await fetchDashboard()
      setData(dashboard)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Błąd połączenia z API')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 60_000)
    return () => clearInterval(interval)
  }, [load])

  const handleScan = async () => {
    setScanning(true)
    try {
      await triggerScan()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Skanowanie nie powiodło się')
    } finally {
      setScanning(false)
    }
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        <p>Ładowanie danych rynkowych...</p>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="error">
        <p>{error}</p>
        <button className="btn btn-primary" onClick={load}>Ponów</button>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="app">
      <header className="header">
        <h1><span>Cyclical</span> Trader</h1>
        <div className="header-meta">
          <div className="status-badge">
            <span className={`status-dot ${data.scanner_running ? '' : 'offline'}`} />
            Skaner {data.scanner_running ? 'aktywny 24/7' : 'offline'}
          </div>
          {data.last_scan_at && (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Ostatni skan: {new Date(data.last_scan_at).toLocaleString('pl-PL')}
            </span>
          )}
          <button className="btn btn-primary" onClick={handleScan} disabled={scanning}>
            {scanning ? 'Skanowanie...' : 'Skanuj teraz'}
          </button>
        </div>
      </header>

      <div className="cycles-grid">
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </div>

      <h2 className="section-title">
        Okazje tradingowe
        <span className="count">{data.opportunities.length}</span>
      </h2>
      {data.opportunities.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', marginBottom: 32 }}>
          Brak aktywnych sygnałów — cykle nie wskazują na wyraźne okazje.
        </p>
      ) : (
        <div className="opportunities-grid">
          {data.opportunities.map((opp) => (
            <OpportunityCard key={`${opp.symbol}-${opp.created_at}`} opp={opp} />
          ))}
        </div>
      )}

      <h2 className="section-title">
        Monitorowane instrumenty
        <span className="count">{data.monitored_assets.length}</span>
      </h2>
      <AssetsTable assets={data.monitored_assets} />

      <footer className="footer">
        Cyclical Trader · Krypto: cykl 364d spadków + 1064d wzrostu od ATH ·
        Tradycyjne: cykl prezydencki USA (lata 1–4 kadencji) ·
        Nie jest to porada inwestycyjna
      </footer>
    </div>
  )
}
