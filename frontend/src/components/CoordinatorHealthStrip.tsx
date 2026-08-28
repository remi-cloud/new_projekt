import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchCoordinatorHealth, type CoordinatorDeskStatus, type CoordinatorHealth } from '../api'
import { useLocale } from '../context/LocaleContext'

function linkGuardBad(lg: CoordinatorDeskStatus['link_guard'] | undefined): number {
  if (!lg) return 0
  return (
    (lg.missing_chain_axiom ?? 0) +
    (lg.bad_4meme ?? 0) +
    (lg.axiom_missing_chain ?? 0) +
    (lg.axiom_bad_4meme ?? 0)
  )
}

function deskTone(st: CoordinatorDeskStatus | undefined): string {
  if (st?.warming_up) return 'flat'
  if (st?.degraded) return 'flat'
  if (st?.ok) return 'ahead'
  return 'behind'
}

function deskLabel(
  st: CoordinatorDeskStatus | undefined,
  t: (key: 'dashboard.coordinatorWarming' | 'dashboard.coordinatorDegraded' | 'dashboard.coordinatorOk' | 'dashboard.coordinatorWarn') => string,
): string {
  if (st?.warming_up) return t('dashboard.coordinatorWarming')
  if (st?.degraded) return t('dashboard.coordinatorDegraded')
  if (st?.ok) return t('dashboard.coordinatorOk')
  return t('dashboard.coordinatorWarn')
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
  const ws = data?.wallet_scout
  const arena = data?.dex_arena
  const clock = data?.session_clock

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
                    n: linkGuardBad(lg),
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
            return (
              <span
                key={key}
                className={`pres-season-chip telemetry-chip-${deskTone(st)}`}
              >
                {t(
                  key === 'launch'
                    ? 'dashboard.coordinatorDeskLaunch'
                    : key === 'axiom'
                      ? 'dashboard.coordinatorDeskAxiom'
                      : 'dashboard.coordinatorDeskFomo',
                )}
                {': '}
                {deskLabel(st, t)}
              </span>
            )
          })}
          {ws && (
            <span className={`pres-season-chip telemetry-chip-${ws.ok ? 'ahead' : 'behind'}`}>
              {t('dashboard.coordinatorWalletScout', {
                bags: ws.open_bags ?? 0,
                w: ws.wallets_scanned ?? 0,
              })}
            </span>
          )}
          {arena && (
            <span className={`pres-season-chip telemetry-chip-${arena.ok ? 'ahead' : 'flat'}`}>
              {t('dashboard.coordinatorDexArena', { n: arena.boards ?? 0 })}
            </span>
          )}
          {clock && (
            <span className={`pres-season-chip telemetry-chip-${clock.ok ? 'ahead' : 'flat'}`}>
              {t('dashboard.coordinatorSessionClock', {
                now: clock.now_session ?? '—',
                hot: clock.hot_lane ?? '—',
              })}
            </span>
          )}
          <Link to="/launch" className="btn btn-ghost tap-target">
            {t('dashboard.coordinatorMemeDesk')}
          </Link>
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
