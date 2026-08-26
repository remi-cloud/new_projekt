import { useEffect, useState } from 'react'
import { fetchAgentTelemetry, type AgentTelemetryResponse } from '../api'
import { RoiEquityChart } from './RoiEquityChart'
import { useLocale } from '../context/LocaleContext'

type TelemetryRange = '7d' | '30d' | '90d' | 'all'
type NavMode = 'portfolio' | 'signal'

function formatSignedPct(delta: number): string {
  const abs = Math.abs(delta).toFixed(1)
  if (delta > 0.05) return `+${abs}`
  if (delta < -0.05) return `−${abs}`
  return abs
}

const RANGES: TelemetryRange[] = ['7d', '30d', '90d', 'all']

export function AgentTelemetryStrip() {
  const { t } = useLocale()
  const [data, setData] = useState<AgentTelemetryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState<TelemetryRange>('30d')
  const [navMode, setNavMode] = useState<NavMode>('portfolio')

  useEffect(() => {
    let alive = true
    const load = () =>
      fetchAgentTelemetry(range)
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
  }, [range])

  const agentCurve = (data?.points || []).map((p) => ({
    time: p.time,
    equity: navMode === 'signal' && p.signal_nav != null ? p.signal_nav : p.agent_nav,
  }))
  const spxCurve = (data?.points || []).map((p) => ({ time: p.time, equity: p.spx_nav }))
  const last = data?.last
  const delta = data?.vs_spx_nav ?? 0
  const ahead = delta > 0.05
  const behind = delta < -0.05
  const tone = ahead ? 'ahead' : behind ? 'behind' : 'flat'
  const signed = formatSignedPct(delta)
  const absPct = Math.abs(delta).toFixed(1)
  const chipDelta = `${ahead ? '+' : behind ? '−' : ''}${absPct}`
  const alphaLabel = ahead
    ? t('dashboard.telemetryAlphaBetter', { delta: `+${absPct}` })
    : behind
      ? t('dashboard.telemetryAlphaWorse', { delta: absPct })
      : t('dashboard.telemetryAlphaFlat')
  const inception = data?.live?.inception_nav
  const inceptionRet =
    inception != null && inception > 0 && last
      ? ((last.agent_nav / inception) - 1) * 100
      : null

  return (
    <section className="dashboard-section agent-telemetry-strip">
      <div className="section-header">
        <h2 className="section-title">{t('dashboard.telemetryTitle')}</h2>
        <div className="telemetry-chips">
          {last && (
            <>
              <span className={`pres-season-chip telemetry-chip-${tone}`}>
                {t('dashboard.telemetryVsSpx', { delta: chipDelta })}
              </span>
              {data?.live?.portfolio_equity_pln != null && (
                <span className="pres-season-chip">
                  {t('dashboard.telemetryEquity', {
                    n: Math.round(data.live.portfolio_equity_pln).toLocaleString(),
                  })}
                </span>
              )}
              <span className={`pres-season-chip ${last.health_ok ? 'season-best_six' : 'season-worst_six'}`}>
                {last.health_ok ? t('dashboard.telemetryOk') : t('dashboard.telemetryWarn')}
              </span>
            </>
          )}
        </div>
      </div>
      <p className="page-lead">{t('dashboard.telemetryLead')}</p>
      <div className="telemetry-controls" role="group" aria-label={t('dashboard.telemetryRange')}>
        {RANGES.map((r) => (
          <button
            key={r}
            type="button"
            className={`btn btn-ghost tap-target telemetry-range-btn${range === r ? ' is-active' : ''}`}
            onClick={() => setRange(r)}
          >
            {r}
          </button>
        ))}
        <button
          type="button"
          className={`btn btn-ghost tap-target telemetry-range-btn${navMode === 'portfolio' ? ' is-active' : ''}`}
          onClick={() => setNavMode('portfolio')}
        >
          {t('dashboard.telemetryAgent')}
        </button>
        <button
          type="button"
          className={`btn btn-ghost tap-target telemetry-range-btn${navMode === 'signal' ? ' is-active' : ''}`}
          onClick={() => setNavMode('signal')}
        >
          {t('dashboard.telemetrySignal')}
        </button>
      </div>
      {data?.disclaimer && <p className="pres-next-term-note">{data.disclaimer}</p>}
      {last && (
        <div className={`telemetry-alpha-sensor telemetry-alpha-${tone}`} aria-live="polite">
          <span className={`telemetry-light telemetry-light-${tone}`} aria-hidden="true" />
          <div className="telemetry-alpha-body">
            <span className="telemetry-alpha-value">{signed}%</span>
            <span className="telemetry-alpha-label">{alphaLabel}</span>
          </div>
        </div>
      )}
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
            {navMode === 'signal' ? t('dashboard.telemetrySignal') : t('dashboard.telemetryAgent')}:{' '}
            {(navMode === 'signal' && last.signal_nav != null
              ? last.signal_nav
              : last.agent_nav
            ).toFixed(1)}
          </span>
          <span>
            {t('dashboard.telemetrySpx')}: {last.spx_nav.toFixed(1)}
          </span>
          <span>
            DD {data?.max_drawdown_pct ?? 0}%
          </span>
          {inceptionRet != null && (
            <span>
              {t('dashboard.telemetryInception', { pct: inceptionRet.toFixed(1) })}
            </span>
          )}
        </div>
      )}
    </section>
  )
}
