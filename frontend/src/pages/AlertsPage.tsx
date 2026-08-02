import { FormEvent, useCallback, useEffect, useState } from 'react'
import {
  fetchAlertLog,
  fetchAlertSettings,
  saveAlertSettings,
  testAlert,
} from '../api'
import LoadingState from '../components/LoadingState'
import {
  actionsForDirection,
  DIRECTION_LABELS,
  SignalDirection,
} from '../lib/labels'
import { AlertLogEntry, AlertSettings } from '../types'

const DIRECTION_OPTIONS: SignalDirection[] = ['long', 'short', 'neutral']

const EMPTY: AlertSettings = {
  enabled: false,
  ntfy_server: 'https://ntfy.sh',
  ntfy_topic: '',
  webhook_url: '',
  min_confidence: 50,
  actions: ['buy', 'sell', 'watch'],
  alert_on_first_seen: false,
}

export default function AlertsPage() {
  const [settings, setSettings] = useState<AlertSettings>(EMPTY)
  const [log, setLog] = useState<AlertLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([fetchAlertSettings(), fetchAlertLog()])
      setSettings(s)
      setLog(l)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się pobrać ustawień alertów')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const directionActive = (dir: SignalDirection) => {
    const needed = actionsForDirection(dir)
    return needed.every((a) => settings.actions.includes(a))
  }

  const toggleDirection = (dir: SignalDirection) => {
    const needed = actionsForDirection(dir)
    setSettings((prev) => {
      const active = needed.every((a) => prev.actions.includes(a))
      if (active) {
        return {
          ...prev,
          actions: prev.actions.filter((a) => !needed.includes(a as typeof needed[number])),
        }
      }
      const merged = new Set([...prev.actions, ...needed])
      return { ...prev, actions: [...merged] }
    })
  }

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const saved = await saveAlertSettings(settings)
      setSettings(saved)
      setMessage('Zapisano ustawienia alertów.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Zapis nie powiódł się')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingState message="Ładowanie alertów…" />

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Alerty</h1>
          <p className="page-lead">
            Powiadomienia przy zmianie sygnału. Kanały: <strong>ntfy</strong> (telefon/desktop) i
            opcjonalny <strong>webhook</strong> (Slack/Discord/własny endpoint).
          </p>
        </div>
        <button
          className="btn btn-primary"
          type="button"
          disabled={saving}
          onClick={async () => {
            setSaving(true)
            setMessage(null)
            try {
              const result = await testAlert()
              setMessage(
                result.ok
                  ? 'Wysłano test alertu.'
                  : result.detail || 'Test nie powiódł się — sprawdź topic/webhook.',
              )
              await load()
            } catch (err) {
              setError(err instanceof Error ? err.message : 'Test nie powiódł się')
            } finally {
              setSaving(false)
            }
          }}
        >
          Wyślij test
        </button>
      </div>

      {error && <p className="inline-error">{error}</p>}
      {message && <p className="inline-ok">{message}</p>}

      <form className="form-panel" onSubmit={handleSave}>
        <label className="check-row">
          <input
            type="checkbox"
            checked={settings.enabled}
            onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
          />
          Alerty włączone
        </label>

        <div className="form-row">
          <label>
            Serwer ntfy
            <input
              value={settings.ntfy_server}
              onChange={(e) => setSettings({ ...settings, ntfy_server: e.target.value })}
              placeholder="https://ntfy.sh"
            />
          </label>
          <label>
            Topic ntfy
            <input
              value={settings.ntfy_topic}
              onChange={(e) => setSettings({ ...settings, ntfy_topic: e.target.value })}
              placeholder="np. cyclical-trader-moj-topic"
            />
          </label>
        </div>

        <label>
          Webhook URL (opcjonalnie)
          <input
            value={settings.webhook_url}
            onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
            placeholder="https://hooks.slack.com/... lub własny endpoint"
          />
        </label>

        <label>
          Min. pewność (%)
          <input
            type="number"
            min={0}
            max={100}
            value={settings.min_confidence}
            onChange={(e) =>
              setSettings({ ...settings, min_confidence: Number(e.target.value) })
            }
          />
        </label>

        <div className="filter-group">
          <span className="filter-label">Alertuj przy kierunku</span>
          <div className="filter-chips">
            {DIRECTION_OPTIONS.map((dir) => (
              <button
                key={dir}
                type="button"
                className={`chip${directionActive(dir) ? ' active' : ''}`}
                onClick={() => toggleDirection(dir)}
              >
                {DIRECTION_LABELS[dir]}
              </button>
            ))}
          </div>
        </div>

        <label className="check-row">
          <input
            type="checkbox"
            checked={settings.alert_on_first_seen}
            onChange={(e) =>
              setSettings({ ...settings, alert_on_first_seen: e.target.checked })
            }
          />
          Alertuj też przy pierwszym pojawieniu się symbolu (nie tylko przy zmianie)
        </label>

        <div className="source-box">
          <h3>Źródła / jak podłączyć ntfy</h3>
          <ol>
            <li>
              Zainstaluj aplikację <a href="https://ntfy.sh" target="_blank" rel="noreferrer">ntfy.sh</a>
            </li>
            <li>Utwórz prywatny topic (np. <code>cyclical-trader-xyz</code>)</li>
            <li>Wklej topic powyżej i kliknij „Wyślij test”</li>
          </ol>
          <p>
            Dane rynkowe: publiczne API notowań (krypto + rynki tradycyjne). Modele scoringu są
            wewnętrzne.
          </p>
        </div>

        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? 'Zapisywanie…' : 'Zapisz ustawienia'}
        </button>
      </form>

      <h2 className="section-title">
        Log dostarczeń
        <span className="count">{log.length}</span>
      </h2>
      {log.length === 0 ? (
        <p className="empty">Brak wysłanych alertów.</p>
      ) : (
        <div className="assets-table-wrap">
          <table className="assets-table">
            <thead>
              <tr>
                <th>Czas</th>
                <th>Kanał</th>
                <th>Status</th>
                <th>Wiadomość</th>
              </tr>
            </thead>
            <tbody>
              {log.map((entry) => (
                <tr key={entry.id}>
                  <td className="cell-sub">
                    {new Date(entry.created_at).toLocaleString('pl-PL')}
                  </td>
                  <td>{entry.channel}</td>
                  <td>
                    <span className={`status-pill status-${entry.status}`}>{entry.status}</span>
                  </td>
                  <td>
                    <div>{entry.message}</div>
                    {entry.detail && <div className="cell-sub">{entry.detail}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
