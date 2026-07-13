import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { ErrorState } from '../components/Loading'
import { useDashboardContext } from '../context/DashboardContext'

export function CyclesPage() {
  const { data, error, reload } = useDashboardContext()

  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="cycles-page">
      <div className="info-banner">
        <h2>Jak działają cykle?</h2>
        <p>
          Aplikacja nie szuka szybkich ruchów cenowych. Bazuje na dwóch ustalonych ramach czasowych,
          które historycznie opisują zachowanie rynków w średnim horyzoncie.
        </p>
      </div>

      <div className="cycles-grid">
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </div>

      <div className="methodology-grid">
        <article className="method-card">
          <h3>Cykl Bitcoin — krypto</h3>
          <ol>
            <li><strong>0–364 dni</strong> od ATH → faza spadkowa, akumulacja</li>
            <li><strong>364–1428 dni</strong> → fala wzrostowa (1064 dni)</li>
            <li><strong>&gt;1428 dni</strong> → dystrybucja, czekaj na nowe ATH</li>
          </ol>
          <p>Dotyczy: BTC, ETH, SOL i pozostałych aktywów krypto.</p>
        </article>
        <article className="method-card">
          <h3>Cykl prezydencki — tradycyjne rynki</h3>
          <ol>
            <li><strong>Rok 1</strong> — słabszy (adaptacja polityki)</li>
            <li><strong>Rok 2</strong> — najsłabszy (midterms)</li>
            <li><strong>Rok 3</strong> — najsilniejszy historycznie</li>
            <li><strong>Rok 4</strong> — umiarkowanie pozytywny (wybory)</li>
          </ol>
          <p>Dotyczy: indeksów USA, akcji, obligacji, surowców, forex.</p>
        </article>
      </div>
    </div>
  )
}
