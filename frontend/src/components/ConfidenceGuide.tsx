export function ConfidenceGuide() {
  return (
    <aside className="confidence-guide" aria-label="Jak czytać pewność sygnału">
      <div className="confidence-guide-head">
        <span className="confidence-guide-title">Pewność sygnału · %</span>
        <span className="confidence-guide-badge">Im wyżej → silniejsza okazja</span>
      </div>
      <p className="confidence-guide-text">
        Liczba przy tagu <strong>Kupuj</strong> lub <strong>Sprzedaj</strong> (np. 80,5%) to zgodność cyklu BTC,
        fazy ceny i momentum. <strong>Im wyższy %, tym lepszy moment</strong> na daną akcję — kupno przy fazie
        spadkowej/akumulacji, sprzedaż przy wzrostowej/dystrybucji.
      </p>
      <div className="confidence-guide-scale">
        <span className="conf-tier conf-tier-high">80%+ silna okazja</span>
        <span className="conf-tier conf-tier-mid">60–79% umiarkowana</span>
        <span className="conf-tier conf-tier-low">&lt;60% słabszy sygnał</span>
      </div>
      <div className="phase-legend">
        <span className="tag phase-tag phase-bearish">Spadkowa</span>
        <span className="phase-legend-desc">faza spadku — potencjalne wejście (KUPUJ)</span>
        <span className="tag phase-tag phase-bullish">Wzrostowa</span>
        <span className="phase-legend-desc">faza wzrostu — rozważ wyjście (SPRZEDAJ)</span>
      </div>
    </aside>
  )
}
