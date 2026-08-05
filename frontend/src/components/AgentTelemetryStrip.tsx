import { useEffect, useState } from 'react'
import { fetchAgentTelemetry, type AgentTelemetryResponse } from '../api'
import { RoiEquityChart } from './RoiEquityChart'
import { useLocale } from '../context/LocaleContext'

export function AgentTelemetryStrip() {
  const { t } = useLocale()
  const [data, setData] = useState<AgentTelemetryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const load = () =>
      fetchAgentTelemetry('30d')
        .then((d) => {
          if (alive) {
            setData(d)
            setError(null)
          }
        })
        .catch((e) => {
          if (alive) setError(e instanceof Error ? e.message : 'telemetry error')
        })
    load()
    const id = window.setInterval(load, 60_000)
    return () => {
      alive = false
      window.clearInterval(id)
    }
  }, [])

  const agentCurve = (data?.points || []).map((p) => ({ time: p.time, equity: p.agent_nav }))
  const spxCurve = (data?.points || []).map((p) => ({ time: p.time, equity: p.spx_nav }))
  const last = data?.last

  return (
    <section className="dashboard-section agent-telemetry-strip">
      <div className="section-header">
        <h2 className="section-title">{t('dashboard.telemetryTitle')}</h2>
        <div className="telemetry-chips">
          {last && (
            <>
              <span className="pres-season-chip">
                {t('dashboard.telemetryLongs', { n: last.n_long })}
              </span>
              <span className="pres-season-chip">
                {t('dashboard.telemetryVsSpx', {
                  delta: (data?.vs_spx_nav ?? 0).toFixed(1),
                })}
              </span>
              <span className={`pres-season-chip ${last.health_ok ? 'season-best_six' : 'season-worst_six'}`}>
                {last.health_ok ? t('dashboard.telemetryOk') : t('dashboard.telemetryWarn')}
              </span>
            </>
          )}
        </div>
      </div>
      <p className="page-lead">{t('dashboard.telemetryLead')}</p>
      {error && <p className="empty-state">{error}</p>}
      {!error && agentCurve.length < 2 && (
        <p className="empty-state">{t('dashboard.telemetryWarmup')}</p>
      )}
      {agentCurve.length >= 2 && (
        <RoiEquityChart equity={agentCurve} buyHold={spxCurve} height={220} />
      )}
      {last && (
        <div className="telemetry-legend">
          <span>
            {t('dashboard.telemetryAgent')}: {last.agent_nav.toFixed(1)}
          </span>
          <span>
            {t('dashboard.telemetrySpx')}: {last.spx_nav.toFixed(1)}
          </span>
          <span>
            DD {data?.max_drawdown_pct ?? 0}%
          </span>
        </div>
      )}
    </section>
  )
}
