import { CycleCardBitcoin } from '../components/CycleCardBitcoin'
import { CycleCardPresidential } from '../components/CycleCardPresidential'
import { CycleCardRegional } from '../components/CycleCardRegional'
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
          Aplikacja łączy cykl Bitcoin (krypto) z regionalnymi cyklami makro (USA, Polska, Europa,
          Azja, EM, globalne) oraz mini-cyklem cenowym (52-tyg. max). Sygnał końcowy waży makro
          regionalne i cenę — przy sprzeczności (np. makro kupuj, cena przy szczytach) dominuje cena.
        </p>
      </div>

      <div className="cycles-grid">
        <CycleCardBitcoin cycle={data.bitcoin_cycle} />
        <CycleCardPresidential cycle={data.presidential_cycle} />
      </div>

      {data.regional_cycles?.length > 0 && (
        <>
          <h3 className="section-title">Cykle makro regionalne</h3>
          <div className="cycles-grid regional-grid">
            {data.regional_cycles.map((c) => (
              <CycleCardRegional key={c.region} cycle={c} />
            ))}
          </div>
        </>
      )}

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
          <h3>Cykl prezydencki — tylko USA</h3>
          <ol>
            <li><strong>Rok 1</strong> — słabszy (adaptacja polityki)</li>
            <li><strong>Rok 2</strong> — najsłabszy (midterms)</li>
            <li><strong>Rok 3</strong> — najsilniejszy historycznie</li>
            <li><strong>Rok 4</strong> — umiarkowanie pozytywny (wybory)</li>
          </ol>
          <p>Dotyczy wyłącznie aktywów z regionem USA (indeksy S&P, NASDAQ, akcje US).</p>
        </article>
        <article className="method-card">
          <h3>Cykle lokalne — reszta świata</h3>
          <ul>
            <li><strong>Polska</strong> — wybory sejmowe, budżet (luty), dywidendy Q4</li>
            <li><strong>Europa</strong> — wybory PE, decyzje ECB, spillover z USA (~35%)</li>
            <li><strong>Azja</strong> — sezonowość JP/CN/IN, Nowy Rok księżycowy</li>
            <li><strong>EM</strong> — wybory Brazylii, spillover Fed (~40%)</li>
            <li><strong>Global</strong> — surowce, forex, obligacje globalne</li>
          </ul>
        </article>
        <article className="method-card">
          <h3>Mini-cykl cenowy (40% wagi)</h3>
          <ol>
            <li><strong>≤3% od 52-tyg. max</strong> → dystrybucja, Sprzedaj</li>
            <li><strong>3–20%</strong> → trend / korekta, Trzymaj / Obserwuj</li>
            <li><strong>&gt;20%</strong> → spadek, Kupuj (strefa dokupowania)</li>
          </ol>
          <p>Przy konflikcie z makro — cena ma pierwszeństwo (waga makro obniżana o 50%).</p>
        </article>
      </div>
    </div>
  )
}
