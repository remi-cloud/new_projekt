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
          <h1>Cykle rynkowe</h1>
          <p className="page-lead">
            Dwa fundamenty: ATH Bitcoina dla krypto oraz 4-letni cykl wyborczy USA dla rynków
            tradycyjnych.
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
            <strong>Krypto:</strong> dni 0–364 od ATH to faza spadkowa (akumulacja); potem ~1064 dni
            fali wzrostowej; końcówka = dystrybucja.
          </li>
          <li>
            <strong>Rok 2 kadencji:</strong> historycznie najsłabszy — sygnał KUPUJ oznacza kupowanie
            dołków, nie „silny rynek”.
          </li>
          <li>
            <strong>Rok 3:</strong> historycznie najsilniejszy dla akcji i indeksów.
          </li>
        </ul>
      </section>
    </div>
  )
}
