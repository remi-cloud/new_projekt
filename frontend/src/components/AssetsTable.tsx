import { Link } from 'react-router-dom'
import { ASSET_LABELS, formatPrice } from '../lib/labels'
import { positionPath } from '../lib/routes'
import { AssetQuote } from '../types'

function ChangeCell({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <span className="change-neutral">—</span>
  const cls = value > 0 ? 'change-positive' : value < 0 ? 'change-negative' : 'change-neutral'
  return (
    <span className={cls}>
      {value > 0 ? '+' : ''}
      {value.toFixed(2)}%
    </span>
  )
}

function SourceTag({ source }: { source?: string }) {
  if (!source || source === 'stub') return <span className="tag source stub">—</span>
  const label =
    source === 'tradingview' ? 'TV' : source === 'coingecko' ? 'CG' : source === 'yahoo' ? 'YH' : source
  return <span className={`tag source ${source}`}>{label}</span>
}

export default function AssetsTable({
  assets,
  showRegion = false,
  showSource = false,
}: {
  assets: AssetQuote[]
  showRegion?: boolean
  showSource?: boolean
}) {
  if (!assets.length) {
    return <div className="empty-block">Brak wierszy do wyświetlenia.</div>
  }

  return (
    <div className="assets-table-wrap">
      <table className="assets-table">
        <thead>
          <tr>
            <th>Instrument</th>
            {showRegion && <th>Region</th>}
            <th>Klasa</th>
            {showSource && <th>Src</th>}
            <th>Cena</th>
            <th>24h</th>
            <th>7d</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => {
            const hasPrice = a.live !== false && typeof a.price === 'number' && a.price > 0
            return (
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
                {showSource && (
                  <td>
                    <SourceTag source={a.quote_source} />
                  </td>
                )}
                <td className="price-cell">
                  {hasPrice ? (
                    <>${formatPrice(a.price, a.asset_class)}</>
                  ) : (
                    <span className="change-neutral">odśwież…</span>
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
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
