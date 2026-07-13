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
            <li>Krypto (BTC, ETH, SOL i inne)</li>
            <li>Indeksy USA, Europa, Azja, Polska (WIG20, WIG, mWIG40, sWIG80)</li>
            <li>Magnificent Seven (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)</li>
            <li>Ekosystem Muska (SpaceX proxy ARKX, Rocket Lab, łańcuch dostaw Tesla)</li>
            <li>Polska — blue chips (PKO, Orlen, Dino, CD Projekt, Allegro…) via Investing.com</li>
            <li>Obligacje, surowce, forex</li>
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
