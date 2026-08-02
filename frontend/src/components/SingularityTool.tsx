import { useState } from 'react'
import { AiTradeSignal } from '../types'
import AiTradeVerdict from './AiTradeVerdict'

/** Singularity as an on-demand tool — not a permanent banner. */
export default function SingularityTool({ ai }: { ai: AiTradeSignal | null | undefined }) {
  const [open, setOpen] = useState(false)

  if (!ai) {
    return (
      <div className="tool-panel muted">
        <div className="tool-panel-bar">
          <span className="tool-panel-name">Singularity</span>
          <span className="cell-sub">Brak werdyktu — odpal skan</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`tool-panel${open ? ' open' : ''}`}>
      <button
        type="button"
        className="tool-panel-bar"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="tool-panel-name">Narzędzie · Singularity</span>
        <span className={`tool-panel-chip signal-${ai.signal}`}>{ai.label}</span>
        <span className="tool-panel-toggle">{open ? 'Zwiń' : 'Uruchom'}</span>
      </button>
      {open && (
        <div className="tool-panel-body">
          <AiTradeVerdict ai={ai} />
        </div>
      )}
    </div>
  )
}
