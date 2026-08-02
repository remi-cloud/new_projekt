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
            Dwa niezależne silniki scoringu — Alpha (aktywa cyfrowe) i Beta (rynki tradycyjne).
            Szczegóły wewnętrzne modeli nie są publikowane.
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
            <strong>LONG</strong> — kierunek wzrostowy: szukaj wejścia long (kupno / long futures).
          </li>
          <li>
            <strong>SHORT</strong> — kierunek spadkowy: szukaj shorta albo redukcji longów.
          </li>
          <li>
            <strong>NEUTRAL</strong> — brak jasnego kierunku: nie forsuj nowej pozycji.
          </li>
          <li>
            <strong>Superokazje</strong> — łączą kierunek z bid/ask, IN/SL/TP i heatmapą liq.
          </li>
        </ul>
      </section>
    </div>
  )
}
