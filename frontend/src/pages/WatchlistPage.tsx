import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  addWatchlistItem,
  fetchWatchlist,
  removeWatchlistItem,
  resetWatchlist,
  toggleWatchlistItem,
} from '../api'
import LoadingState, { ErrorState } from '../components/LoadingState'
import { ASSET_LABELS } from '../lib/labels'
import { AssetClass, CatalogAsset, WatchlistItem } from '../types'

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [catalog, setCatalog] = useState<CatalogAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [assetClass, setAssetClass] = useState<AssetClass>('stock')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await fetchWatchlist()
      setItems(data.items)
      setCatalog(data.catalog)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się pobrać watchlisty')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onWatch = useMemo(() => new Set(items.map((i) => i.symbol)), [items])

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!symbol.trim()) return
    setBusy(true)
    try {
      await addWatchlistItem({
        symbol: symbol.trim(),
        name: name.trim() || undefined,
        asset_class: assetClass,
      })
      setSymbol('')
      setName('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dodawanie nie powiodło się')
    } finally {
      setBusy(false)
    }
  }

  const handleAddCatalog = async (asset: CatalogAsset) => {
    setBusy(true)
    try {
      await addWatchlistItem(asset)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dodawanie nie powiodło się')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingState message="Ładowanie watchlisty…" />
  if (error && items.length === 0) return <ErrorState message={error} onRetry={load} />

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Watchlista</h1>
          <p className="page-lead">
            Wybierz instrumenty, które skaner ma monitorować. Źródła: CoinGecko (krypto) i Yahoo
            Finance (reszta).
          </p>
        </div>
        <button
          className="btn btn-ghost"
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await resetWatchlist()
              await load()
            } finally {
              setBusy(false)
            }
          }}
        >
          Reset do domyślnych
        </button>
      </div>

      {error && <p className="inline-error">{error}</p>}

      <form className="form-panel" onSubmit={handleAdd}>
        <h2 className="section-title">Dodaj instrument</h2>
        <div className="form-row">
          <label>
            Symbol
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="np. TSLA lub BTC-USD"
              required
            />
          </label>
          <label>
            Nazwa
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="opcjonalnie"
            />
          </label>
          <label>
            Klasa
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value as AssetClass)}
            >
              {(Object.keys(ASSET_LABELS) as AssetClass[]).map((c) => (
                <option key={c} value={c}>
                  {ASSET_LABELS[c]}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            Dodaj
          </button>
        </div>
      </form>

      <h2 className="section-title">
        Aktywna lista
        <span className="count">{items.length}</span>
      </h2>
      <div className="assets-table-wrap">
        <table className="assets-table">
          <thead>
            <tr>
              <th>Instrument</th>
              <th>Klasa</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.symbol} className={item.enabled ? '' : 'row-muted'}>
                <td>
                  <strong>{item.name}</strong>
                  <div className="cell-sub">{item.symbol}</div>
                </td>
                <td>
                  <span className={`tag ${item.asset_class}`}>
                    {ASSET_LABELS[item.asset_class]}
                  </span>
                </td>
                <td>{item.enabled ? 'Monitorowany' : 'Wyłączony'}</td>
                <td className="actions-cell">
                  <button
                    className="btn btn-ghost btn-sm"
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true)
                      try {
                        await toggleWatchlistItem(item.symbol, !item.enabled)
                        await load()
                      } finally {
                        setBusy(false)
                      }
                    }}
                  >
                    {item.enabled ? 'Wyłącz' : 'Włącz'}
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    type="button"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true)
                      try {
                        await removeWatchlistItem(item.symbol)
                        await load()
                      } finally {
                        setBusy(false)
                      }
                    }}
                  >
                    Usuń
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="section-title">Katalog domyślny</h2>
      <div className="catalog-grid">
        {catalog.map((asset) => {
          const watched = onWatch.has(asset.symbol)
          return (
            <button
              key={asset.symbol}
              type="button"
              className={`catalog-chip${watched ? ' on' : ''}`}
              disabled={busy || watched}
              onClick={() => handleAddCatalog(asset)}
            >
              <strong>{asset.symbol}</strong>
              <span>{asset.name}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
