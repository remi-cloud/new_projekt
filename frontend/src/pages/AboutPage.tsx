export function AboutPage() {
  return (
    <div className="about-page">
      <article className="about-card">
        <h2>Cyclical Trader — wersja WWW</h2>
        <p>
          Aplikacja webowa do monitorowania rynków finansowych 24/7 i identyfikacji okazji
          inwestycyjnych opartych na cyklach — bez skalpingu i wysokiej częstotliwości transakcji.
        </p>
      </article>

      <div className="about-grid">
        <article className="about-card">
          <h3>Monitorowane rynki</h3>
          <ul>
            <li>Krypto (BTC, ETH, SOL)</li>
            <li>Indeksy USA (S&P 500, Dow, NASDAQ, Russell)</li>
            <li>Akcje (AAPL, MSFT, NVDA, JPM)</li>
            <li>Obligacje (TLT, IEF, LQD, HYG)</li>
            <li>Surowce (złoto, srebro, ropa, gaz)</li>
            <li>Forex (EUR/USD, GBP/USD, USD/JPY, DXY)</li>
          </ul>
        </article>
        <article className="about-card">
          <h3>Technologia</h3>
          <ul>
            <li>Frontend: React + TypeScript (SPA)</li>
            <li>Backend: FastAPI + APScheduler</li>
            <li>Dane: CoinGecko + Yahoo Finance</li>
            <li>Skanowanie: co 15 minut, 24/7</li>
          </ul>
        </article>
        <article className="about-card">
          <h3>Disclaimer</h3>
          <p>
            Ta aplikacja służy wyłącznie celom edukacyjno-analitycznym.
            Nie stanowi porady inwestycyjnej. Trading wiąże się z ryzykiem utraty kapitału.
            Zawsze przeprowadź własną analizę przed podjęciem decyzji.
          </p>
        </article>
      </div>
    </div>
  )
}
