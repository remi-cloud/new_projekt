import { ASSET_LABELS, DIRECTION_LABELS, SignalDirection } from '../lib/labels'
import { AssetClass } from '../types'

type Props = {
  assetClass: AssetClass | 'all'
  onAssetClass: (v: AssetClass | 'all') => void
  direction?: SignalDirection | 'all'
  onDirection?: (v: SignalDirection | 'all') => void
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

const DIRECTIONS: Array<SignalDirection | 'all'> = ['all', 'long', 'short', 'neutral']

export default function FilterBar({
  assetClass,
  onAssetClass,
  direction = 'all',
  onDirection,
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
      {showAction && onDirection && (
        <div className="filter-group">
          <span className="filter-label">Kierunek</span>
          <div className="filter-chips">
            {DIRECTIONS.map((d) => (
              <button
                key={d}
                type="button"
                className={`chip${direction === d ? ' active' : ''}`}
                onClick={() => onDirection(d)}
              >
                {d === 'all' ? 'Wszystkie' : DIRECTION_LABELS[d]}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
