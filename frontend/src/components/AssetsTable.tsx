import { Link } from 'react-router-dom'
import { ASSET_LABELS, formatPrice } from '../lib/labels'
import { positionPath } from '../lib/routes'
import { AssetQuote } from '../types'

function ChangeCell({ value }: { value: number | null }) {
  if (value === null) return <span className="change-neutral">—</span>
  const cls = value > 0 ? 'change-positive' : value < 0 ? 'change-negative' : 'change-neutral'
  return (
    <span className={cls}>
      {value > 0 ? '+' : ''}
      {value.toFixed(2)}%
    </span>
  )
}

export default function AssetsTable({
  assets,
  showRegion = false,
}: {
  assets: AssetQuote[]
  showRegion?: boolean
}) {
  return (
    <div className="assets-table-wrap">
      <table className="assets-table">
        <thead>
          <tr>
            <th>Instrument</th>
            {showRegion && <th>Region</th>}
            <th>Klasa</th>
            <th>Cena</th>
            <th>24h</th>
            <th>7d</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => (
            <tr key={a.symbol} className="row-link">
              <td>
                <Link to={positionPath(a.symbol)} className="row-main-link">
                  <strong>{a.name}</strong>
                  <div className="cell-sub">{a.symbol}</div>
                </Link>
              </td>
              {showRegion && (
                <td>
                  <span className="tag region">{a.region_label ?? a.region ?? '—'}</span>
                </td>
              )}
              <td>
                <span className={`tag ${a.asset_class}`}>{ASSET_LABELS[a.asset_class]}</span>
              </td>
              <td className="price-cell">
                {a.live === false || a.price <= 0 ? (
                  <span className="change-neutral">brak notowań</span>
                ) : (
                  <>${formatPrice(a.price, a.asset_class)}</>
                )}
              </td>
              <td>
                <ChangeCell value={a.change_pct_24h} />
              </td>
              <td>
                <ChangeCell value={a.change_pct_7d} />
              </td>
              <td>
                <Link to={positionPath(a.symbol)} className="btn btn-ghost btn-sm">
                  Otwórz
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
