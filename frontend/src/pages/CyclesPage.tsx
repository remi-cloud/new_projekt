import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { CycleCardRegional } from '../components/CycleCardRegional'
import { ErrorState, Loading } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'
import { useLocale } from '../context/LocaleContext'

export function CyclesPage() {
  const { data, error, reload, loading } = useDashboardContext()
  const { t, tArray } = useLocale()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (loading && !data) return <Loading message={t('layout.loading')} />
  if (!data) return null

  const methodBtcItems = tArray('cycles.methodBtcItems')
  const methodPresItems = tArray('cycles.methodPresItems')
  const methodLocalItems = tArray('cycles.methodLocalItems')
  const methodMiniItems = tArray('cycles.methodMiniItems')

  return (
    <div className="cycles-page">
      <div className="info-banner">
        <h2>{t('cycles.infoTitle')}</h2>
        <p>{t('cycles.infoBody')}</p>
      </div>

      <div className="cycles-grid">
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </div>

      {data.regional_cycles?.length > 0 && (
        <>
          <h3 className="section-title">{t('cycles.regionalTitle')}</h3>
          <div className="cycles-grid regional-grid">
            {data.regional_cycles.map((c) => (
              <CycleCardRegional key={c.region} cycle={c} />
            ))}
          </div>
        </>
      )}

      <div className="methodology-grid">
        <article className="method-card">
          <h3>{t('cycles.methodBtcTitle')}</h3>
          <ol>
            {methodBtcItems.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
          <p>{t('cycles.methodBtcNote')}</p>
        </article>
        <article className="method-card">
          <h3>{t('cycles.methodPresTitle')}</h3>
          <ol>
            {methodPresItems.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
          <p>{t('cycles.methodPresNote')}</p>
        </article>
        <article className="method-card">
          <h3>{t('cycles.methodLocalTitle')}</h3>
          <ul>
            {methodLocalItems.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="method-card">
          <h3>{t('cycles.methodMiniTitle')}</h3>
          <ol>
            {methodMiniItems.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
          <p>{t('cycles.methodMiniNote')}</p>
        </article>
      </div>
    </div>
  )
}
