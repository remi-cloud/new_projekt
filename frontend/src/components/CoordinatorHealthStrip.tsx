import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchCoordinatorHealth, type CoordinatorHealth } from '../api'
import { useLocale } from '../context/LocaleContext'

function deskTone(ok: boolean | undefined, warming?: boolean): string {
  if (warming) return 'flat'
  if (ok) return 'ahead'
  return 'behind'
}

export function CoordinatorHealthStrip() {
  const { t, dateLocale } = useLocale()
  const [data, setData] = useState<CoordinatorHealth | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const load = () =>
      fetchCoordinatorHealth()
        .then((d) => {
          if (alive) {
            setData(d)
            setError(null)
          }
        })
        .catch((e) => {
          if (alive) setError(e instanceof Error ? e.message : 'coordinator error')
        })
    load()
    const id = window.setInterval(load, 90_000)
    return () => {
      alive = false
      window.clearInterval(id)
    }
  }, [])

  const desks = data?.desks
  const lg = desks?.launch?.link_guard
  const tone = data?.ok ? 'ahead' : data?.startup_grace ? 'flat' : 'behind'

  return (
    <section className="dashboard-section coordinator-health-strip">
      <div className="section-header">
        <h2 className="section-title">{t('dashboard.coordinatorTitle')}</h2>
        <div className="telemetry-chips">
          {data && (
            <>
              <span className={`pres-season-chip telemetry-chip-${tone}`}>
                {data.ok
                  ? t('dashboard.coordinatorOk')
                  : data.startup_grace
                    ? t('dashboard.coordinatorWarming')
                    : t('dashboard.coordinatorWarn')}
              </span>
              {lg && (
                <span className={`pres-season-chip ${lg.ok ? 'season-best_six' : 'season-worst_six'}`}>
                  {t('dashboard.coordinatorLinkGuard', {
                    n: (lg.missing_chain_axiom ?? 0) + (lg.bad_4meme ?? 0),
                  })}
                </span>
              )}
            </>
          )}
        </div>
      </div>
      <p className="page-lead">{t('dashboard.coordinatorLead')}</p>
      {error && <p className="empty-state">{error}</p>}
      {desks && (
        <div className="coordinator-desk-row">
          {(['launch', 'axiom', 'fomo'] as const).map((key) => {
            const st = desks[key]
            const warming = Boolean(st?.warming_up)
            return (
              <span
                key={key}
                className={`pres-season-chip telemetry-chip-${deskTone(st?.ok, warming)}`}
              >
                {t(
                  key === 'launch'
                    ? 'dashboard.coordinatorDeskLaunch'
                    : key === 'axiom'
                      ? 'dashboard.coordinatorDeskAxiom'
                      : 'dashboard.coordinatorDeskFomo',
                )}
                {': '}
                {warming
                  ? t('dashboard.coordinatorWarming')
                  : st?.ok
                    ? t('dashboard.coordinatorOk')
                    : t('dashboard.coordinatorWarn')}
              </span>
            )
          })}
          <Link to="/narzedzia" className="btn btn-ghost tap-target">
            {t('dashboard.coordinatorTools')}
          </Link>
        </div>
      )}
      {data?.at && (
        <p className="pres-next-term-note">
          {t('dashboard.coordinatorAt', {
            date: new Date(data.at).toLocaleString(dateLocale),
          })}
        </p>
      )}
    </section>
  )
}
