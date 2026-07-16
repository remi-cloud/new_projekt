import { useDomainLabels } from '../i18n/useDomainLabels'
import { useLocale } from '../context/LocaleContext'
import { formatPrice } from '../utils/format'
import { AssetClass, AssetQuote } from '../types'

function ChangeCell({ value }: { value: number | null }) {
  if (value === null) return <span className="change-neutral">—</span>
  const cls = value > 0 ? 'change-positive' : value < 0 ? 'change-negative' : 'change-neutral'
  return <span className={cls}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
}

export function AssetsTable({ assets }: { assets: AssetQuote[] }) {
  const { t } = useLocale()
  const { asset: assetLabels } = useDomainLabels()

  if (!assets.length) {
    return <p className="empty-state">{t('table.noMarketData')}</p>
  }

  return (
    <div className="assets-table-wrap">
      <table className="assets-table">
        <thead>
          <tr>
            <th>{t('table.instrument')}</th>
            <th>{t('table.class')}</th>
            <th>{t('table.price')}</th>
            <th>{t('table.change24h')}</th>
            <th>{t('table.change7d')}</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => (
            <tr key={a.symbol}>
              <td>
                <strong>{a.name}</strong>
                <div className="symbol-sub">{a.symbol}</div>
              </td>
              <td><span className={`tag ${a.asset_class}`}>{assetLabels[a.asset_class]}</span></td>
              <td className="price-cell">${formatPrice(a.price, a.asset_class)}</td>
              <td><ChangeCell value={a.change_pct_24h} /></td>
              <td><ChangeCell value={a.change_pct_7d} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function filterAssets(assets: AssetQuote[], assetClass: AssetClass | 'all') {
  if (assetClass === 'all') return assets
  return assets.filter((a) => a.asset_class === assetClass)
}
