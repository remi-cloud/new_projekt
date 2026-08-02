import { AiTradeSignal } from '../types'

export default function AiTradeVerdict({ ai }: { ai: AiTradeSignal }) {
  const buyPct = Math.max(ai.buy_score, 0) + Math.max(ai.sell_score, 0)
  const buyShare = buyPct > 0 ? (ai.buy_score / buyPct) * 100 : 50
  const sellShare = 100 - buyShare

  return (
    <section className={`ai-verdict ai-verdict-${ai.signal}`} aria-label="Konsultacja AI">
      <div className="ai-verdict-head">
        <span className="ai-verdict-tag">Konsultacja AI</span>
        <div className="ai-verdict-main">
          <strong className={`ai-verdict-label signal-${ai.signal}`}>{ai.label}</strong>
          <span className="ai-verdict-conf">{ai.confidence.toFixed(0)}% pewności</span>
        </div>
        <p className="ai-verdict-summary">{ai.summary}</p>
        <p className="ai-verdict-detail">{ai.verdict_detail}</p>
        {(ai.aligned || ai.conflict) && (
          <p className={`ai-verdict-align ${ai.conflict ? 'bad' : 'good'}`}>
            {ai.aligned && 'Czynniki zgodne — model + liq AI w jednym kierunku.'}
            {ai.conflict && 'Konflikt czynników — model i liq AI wskazują przeciwnie.'}
          </p>
        )}
      </div>

      <div className="ai-score-bars" aria-hidden>
        <div className="ai-score-row">
          <span>KUP</span>
          <div className="ai-score-track">
            <div className="ai-score-fill kup" style={{ width: `${buyShare}%` }} />
          </div>
          <em>{ai.buy_score.toFixed(0)}</em>
        </div>
        <div className="ai-score-row">
          <span>SPRZEDAJ</span>
          <div className="ai-score-track">
            <div className="ai-score-fill sprzedaj" style={{ width: `${sellShare}%` }} />
          </div>
          <em>{ai.sell_score.toFixed(0)}</em>
        </div>
      </div>

      <h4 className="ai-factors-title">Czynniki w konsultacji</h4>
      <ul className="ai-factors">
        {ai.factors.map((f) => (
          <li key={`${f.name}-${f.detail}`} className={`ai-factor side-${f.side}`}>
            <div className="ai-factor-top">
              <strong>{f.name}</strong>
              <span className={`ai-factor-side side-${f.side}`}>
                {f.side === 'kup' ? 'KUP' : f.side === 'sprzedaj' ? 'SPRZEDAJ' : 'CZEKAJ'}
                {f.weight !== 0 ? ` · ${f.weight > 0 ? '+' : ''}${f.weight}` : ''}
              </span>
            </div>
            <p>{f.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
