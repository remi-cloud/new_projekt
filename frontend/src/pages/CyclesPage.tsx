import { CycleCardAlpha, CycleCardBeta } from '../components/CycleCards'
import { AlphaTimeline, BetaTimeline } from '../components/CycleTimeline'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { useDashboard } from '../hooks/useDashboard'

export default function CyclesPage() {
  const { data, loading, error, load } = useDashboard()

  if (loading) return <LoadingState />
  if (error && !data) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Modele sygnałowe</h1>
          <p className="page-lead">
            Dwa niezależne silniki — nie gryzą się nawzajem. Alpha liczy tylko krypto,
            Beta tylko rynki tradycyjne. Singularity łączy scouting LONG/SHORT per instrument
            (trend-first, bez sztucznego 50/50).
          </p>
        </div>
      </div>

      <div className="cycles-grid">
        <CycleCardAlpha model={data.alpha_model} />
        <CycleCardBeta model={data.beta_model} />
      </div>

      <AlphaTimeline model={data.alpha_model} />
      <BetaTimeline model={data.beta_model} />

      <section className="info-block reveal">
        <h3>Jak czytać sygnały</h3>
        <ul>
          <li>
            <strong>Model Alpha</strong> — wyłącznie BTC/ETH/SOL (cykl cyfrowy). Nie wpływa na akcje ani indeksy.
          </li>
          <li>
            <strong>Model Beta</strong> — akcje, indeksy, obligacje, FX, surowce. Nie wpływa na krypto.
          </li>
          <li>
            <strong>LONG / SHORT</strong> — scoutdzi polują osobno, ale na jeden symbol zostaje jedna strona
            (wygrywa trend 7d; słabe sygnały nie dopełniają „parytetu”).
          </li>
          <li>
            <strong>Superokazje + Singularity</strong> — po konsultacji czynników: <strong>KUP</strong>,{' '}
            <strong>SPRZEDAJ</strong> albo <strong>CZEKAJ</strong> przy prawdziwym konflikcie.
          </li>
        </ul>
      </section>
    </div>
  )
}
