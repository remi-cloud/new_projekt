import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProgramUs1995, type ProgramUsBacktestResponse } from '../api'
import { RoiEquityChart } from './RoiEquityChart'
import { useLocale } from '../context/LocaleContext'

function fmt(n: number | undefined | null): string {
  if (n == null || Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

export function ProgramUsBacktestPanel() {
  const { t } = useLocale()
  const [data, setData] = useState<ProgramUsBacktestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    fetchProgramUs1995(1000)
      .then((d) => {
        if (alive) {
          setData(d)
          setError(null)
        }
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : 'backtest error')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const equity = (data?.equity_curve || []).map((p) => ({ time: p.time, equity: p.equity }))
  const bh = (data?.buy_hold?.equity_curve || []).map((p) => ({ time: p.time, equity: p.equity }))
  const prog = data?.program

  return (
    <section className="dashboard-section program-us-backtest">
      <div className="section-header">
        <h2 className="section-title">{t('dashboard.programTitle')}</h2>
        <Link to="/narzedzia/roi" className="link-btn tap-target card-nav-link">
          {t('dashboard.programFullRoi')}
        </Link>
      </div>
      <p className="page-lead">{t('dashboard.programLead')}</p>
      {loading && <p className="empty-state">{t('layout.loading')}</p>}
      {error && <p className="empty-state">{error}</p>}
      {data && prog && (
        <>
          <div className="program-stats">
            <div className="stat">
              <div className="stat-label">{t('dashboard.programAgent')}</div>
              <div className="stat-value">${fmt(prog.agent_final)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t('dashboard.programBh')}</div>
              <div className="stat-value">${fmt(prog.buy_hold_final)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">CAGR</div>
              <div className="stat-value">{data.cagr_pct?.toFixed(1)}%</div>
            </div>
            <div className="stat">
              <div className="stat-label">Ratio</div>
              <div className="stat-value">{prog.ratio_agent_vs_bh ?? '—'}</div>
            </div>
          </div>
          {equity.length >= 2 && <RoiEquityChart equity={equity} buyHold={bh} height={240} />}
          <p className="pres-next-term-note">{prog.disclaimer || data.disclaimer}</p>
        </>
      )}
    </section>
  )
}
