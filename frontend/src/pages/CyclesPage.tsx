import { CycleCardBitcoin, CycleCardPresidential } from '../components/CycleCards'
import { BitcoinTimeline, PresidentialTimeline } from '../components/CycleTimeline'
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
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </div>

      <BitcoinTimeline cycle={data.bitcoin_cycle} />
      <PresidentialTimeline cycle={data.presidential_cycle} />

      <section className="info-block reveal">
        <h3>Jak czytać sygnały</h3>
        <ul>
          <li>
            <strong>Kupuj / Obserwuj:</strong> model wskazuje strefę akumulacji lub kontynuacji.
          </li>
          <li>
            <strong>Trzymaj:</strong> brak agresywnego dokupywania — zarządzaj otwartą ekspozycją.
          </li>
          <li>
            <strong>Sprzedaj:</strong> preferuj redukcję ryzyka / realizację.
          </li>
          <li>
            <strong>Superokazje:</strong> łączą modele z bid/ask, poziomami wejścia/wyjścia i heatmapą
            liq.
          </li>
        </ul>
      </section>
    </div>
  )
}
