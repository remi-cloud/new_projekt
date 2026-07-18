import { ASSET_LABELS, SIGNAL_LABELS } from '../lib/labels'
import { AssetClass, SignalAction } from '../types'

type Props = {
  assetClass: AssetClass | 'all'
  onAssetClass: (v: AssetClass | 'all') => void
  action?: SignalAction | 'all'
  onAction?: (v: SignalAction | 'all') => void
  showAction?: boolean
}

const CLASSES: Array<AssetClass | 'all'> = [
  'all',
  'crypto',
  'stock',
  'index',
  'bond',
  'commodity',
  'forex',
]

const ACTIONS: Array<SignalAction | 'all'> = ['all', 'buy', 'sell', 'hold', 'watch']

export default function FilterBar({
  assetClass,
  onAssetClass,
  action = 'all',
  onAction,
  showAction = true,
}: Props) {
  return (
    <div className="filters">
      <div className="filter-group">
        <span className="filter-label">Klasa</span>
        <div className="filter-chips">
          {CLASSES.map((c) => (
            <button
              key={c}
              type="button"
              className={`chip${assetClass === c ? ' active' : ''}`}
              onClick={() => onAssetClass(c)}
            >
              {c === 'all' ? 'Wszystkie' : ASSET_LABELS[c]}
            </button>
          ))}
        </div>
      </div>
      {showAction && onAction && (
        <div className="filter-group">
          <span className="filter-label">Sygnał</span>
          <div className="filter-chips">
            {ACTIONS.map((a) => (
              <button
                key={a}
                type="button"
                className={`chip${action === a ? ' active' : ''}`}
                onClick={() => onAction(a)}
              >
                {a === 'all' ? 'Wszystkie' : SIGNAL_LABELS[a]}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
