import { useEffect, useState } from 'react'
import { fetchNotificationStatus, saveAlertSettings } from '../api'
import { subscribeToPush } from '../hooks/useLiveFeed'
import { ErrorState } from '../components/Loading'
import { AlertSettings, NotificationStatus } from '../types'

export function AlertsPage() {
  const [status, setStatus] = useState<NotificationStatus | null>(null)
  const [settings, setSettings] = useState<AlertSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchNotificationStatus()
      .then((s) => {
        setStatus(s)
        setSettings(s.settings)
      })
      .catch(() => setError('Nie udało się załadować ustawień'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    setMessage(null)
    try {
      const saved = await saveAlertSettings(settings)
      setSettings(saved)
      setMessage('Ustawienia zapisane ✓')
    } catch {
      setMessage('Błąd zapisu ustawień')
    } finally {
      setSaving(false)
    }
  }

  const handleEnablePush = async () => {
    if (!status?.vapid_public_key) {
      setMessage('Push niedostępny — brak klucza VAPID na serwerze')
      return
    }
    try {
      await subscribeToPush(status.vapid_public_key)
      setMessage('Powiadomienia push włączone ✓')
      const s = await fetchNotificationStatus()
      setStatus(s)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Nie udało się włączyć push')
    }
  }

  if (loading) return <div className="page-loading">Ładowanie...</div>
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />
  if (!settings || !status) return null

  return (
    <div className="alerts-page">
      <div className="info-banner">
        <h2>Powiadomienia</h2>
        <p>
          Aplikacja śledzi rynki w czasie rzeczywistym (odświeżanie cen co ~30 s) i wysyła alerty
          przy zmianie sygnału lub wysokiej pewności. Handel pozostaje manualny — powiadomienia
          tylko informują o okazjach.
        </p>
      </div>

      <section className="settings-card">
        <h3>Push (przeglądarka / telefon)</h3>
        <p className="settings-hint">
          Status: {status.push_configured ? 'skonfigurowany' : 'brak VAPID'} · Subskrypcje: {status.push_subscriptions}
        </p>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.push_enabled}
            onChange={(e) => setSettings({ ...settings, push_enabled: e.target.checked })}
          />
          Wysyłaj powiadomienia push
        </label>
        <button type="button" className="btn-primary tap-target" onClick={handleEnablePush}>
          Włącz push w tej przeglądarce
        </button>
      </section>

      <section className="settings-card">
        <h3>SMS (Twilio)</h3>
        <p className="settings-hint">
          Status: {status.sms_configured ? 'Twilio skonfigurowane' : 'Ustaw CYCLICAL_TWILIO_* na serwerze'}
        </p>
        <label className="field-label">
          Numer telefonu (E.164, np. +48123456789)
          <input
            type="tel"
            className="field-input"
            value={settings.phone}
            onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
            placeholder="+48..."
          />
        </label>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.sms_enabled}
            onChange={(e) => setSettings({ ...settings, sms_enabled: e.target.checked })}
          />
          Wysyłaj SMS przy alertach
        </label>
      </section>

      <section className="settings-card">
        <h3>Progi alertów</h3>
        <label className="field-label">
          Minimalna pewność sygnału ({settings.min_confidence}%)
          <input
            type="range"
            min={40}
            max={95}
            value={settings.min_confidence}
            onChange={(e) => setSettings({ ...settings, min_confidence: Number(e.target.value) })}
          />
        </label>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.alert_on_signal_change}
            onChange={(e) => setSettings({ ...settings, alert_on_signal_change: e.target.checked })}
          />
          Alert przy zmianie sygnału (Kupuj ↔ Sprzedaj)
        </label>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.alert_on_new_opportunity}
            onChange={(e) => setSettings({ ...settings, alert_on_new_opportunity: e.target.checked })}
          />
          Alert przy nowej okazji
        </label>
      </section>

      <button type="button" className="btn-primary tap-target" onClick={handleSave} disabled={saving}>
        {saving ? 'Zapisywanie…' : 'Zapisz ustawienia'}
      </button>

      {message && <p className="settings-message">{message}</p>}
    </div>
  )
}
