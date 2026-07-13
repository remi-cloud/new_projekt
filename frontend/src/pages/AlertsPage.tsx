import { useEffect, useState } from 'react'
import {
  fetchNotificationStatus,
  saveAlertSettings,
  saveTwilioConfig,
  testNotifications,
} from '../api'
import { subscribeToPush } from '../hooks/useLiveFeed'
import { ErrorState } from '../components/Loading'
import { AlertSettings, NotificationStatus, TwilioConfig } from '../types'

export function AlertsPage() {
  const [status, setStatus] = useState<NotificationStatus | null>(null)
  const [settings, setSettings] = useState<AlertSettings | null>(null)
  const [twilio, setTwilio] = useState<TwilioConfig>({ account_sid: '', auth_token: '', from_number: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = () =>
    fetchNotificationStatus()
      .then((s) => {
        setStatus(s)
        setSettings(s.settings)
      })
      .catch(() => setError('Nie udało się załadować ustawień'))

  useEffect(() => {
    reload().finally(() => setLoading(false))
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
      await reload()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Nie udało się włączyć push')
    }
  }

  const handleSaveTwilio = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await saveTwilioConfig(twilio)
      setTwilio((t) => ({ ...t, auth_token: '' }))
      setMessage('Dane Twilio zapisane na serwerze ✓')
      await reload()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Błąd zapisu Twilio')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setMessage(null)
    try {
      const res = await testNotifications()
      const ntfy = res.ntfy as { ok?: boolean; url?: string } | undefined
      const sms = res.sms as { ok?: boolean; message?: string } | undefined
      if (ntfy?.ok) {
        setMessage(`Test ntfy wysłany — sprawdź aplikację ntfy (${ntfy.url})`)
      } else if (sms?.ok) {
        setMessage(`Test SMS wysłany na ${settings?.phone}`)
      } else {
        setMessage(sms?.message || 'Test wysłany (ntfy) — sprawdź telefon')
      }
    } catch {
      setMessage('Test nie powiódł się')
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
          Alerty na <strong>{settings.phone}</strong>. Handel manualny — aplikacja tylko informuje
          o sygnałach. Kanał <strong>ntfy</strong> działa od razu (bez konta). SMS wymaga Twilio.
        </p>
      </div>

      <section className="settings-card highlight-card">
        <h3>📱 Telefon — ntfy (działa od razu)</h3>
        <p className="settings-hint">
          1. Zainstaluj aplikację <strong>ntfy</strong> (Android/iOS)<br />
          2. Dodaj subskrypcję tego tematu:
        </p>
        <code className="topic-code">{status.ntfy_subscribe_url || settings.ntfy_topic}</code>
        {status.ntfy_app_url && (
          <a className="btn-link tap-target" href={status.ntfy_app_url}>
            Otwórz w aplikacji ntfy
          </a>
        )}
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.ntfy_enabled}
            onChange={(e) => setSettings({ ...settings, ntfy_enabled: e.target.checked })}
          />
          Wysyłaj alerty na telefon (ntfy)
        </label>
      </section>

      <section className="settings-card">
        <h3>SMS — Twilio (+39…)</h3>
        <p className="settings-hint">
          {status.sms_configured
            ? 'Twilio skonfigurowane ✓'
            : 'Załóż konto na twilio.com/try-twilio (Włochy obsługiwane), zweryfikuj , wklej dane poniżej:'}
        </p>
        <label className="field-label">
          Account SID (AC…)
          <input
            className="field-input"
            value={twilio.account_sid}
            onChange={(e) => setTwilio({ ...twilio, account_sid: e.target.value })}
            placeholder="ACxxxxxxxx"
            autoComplete="off"
          />
        </label>
        <label className="field-label">
          Auth Token
          <input
            className="field-input"
            type="password"
            value={twilio.auth_token}
            onChange={(e) => setTwilio({ ...twilio, auth_token: e.target.value })}
            placeholder="••••••••"
            autoComplete="new-password"
          />
        </label>
        <label className="field-label">
          Numer nadawcy Twilio (E.164)
          <input
            className="field-input"
            value={twilio.from_number}
            onChange={(e) => setTwilio({ ...twilio, from_number: e.target.value })}
            placeholder="+39..."
          />
        </label>
        <label className="field-label">
          Twój numer (odbiorca)
          <input
            type="tel"
            className="field-input"
            value={settings.phone}
            onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
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
        <button type="button" className="btn-secondary tap-target" onClick={handleSaveTwilio} disabled={saving}>
          Zapisz dane Twilio
        </button>
      </section>

      <section className="settings-card">
        <h3>Push (przeglądarka)</h3>
        <p className="settings-hint">
          Subskrypcje: {status.push_subscriptions}
        </p>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.push_enabled}
            onChange={(e) => setSettings({ ...settings, push_enabled: e.target.checked })}
          />
          Wysyłaj powiadomienia push
        </label>
        <button type="button" className="btn-secondary tap-target" onClick={handleEnablePush}>
          Włącz push w tej przeglądarce
        </button>
      </section>

      <section className="settings-card">
        <h3>Progi alertów</h3>
        <label className="field-label">
          Minimalna pewność ({settings.min_confidence}%)
          <input
            type="range"
            min={40}
            max={95}
            value={settings.min_confidence}
            onChange={(e) => setSettings({ ...settings, min_confidence: Number(e.target.value) })}
          />
        </label>
      </section>

      <button type="button" className="btn-primary tap-target" onClick={handleSave} disabled={saving}>
        {saving ? 'Zapisywanie…' : 'Zapisz ustawienia'}
      </button>
      <button type="button" className="btn-secondary tap-target" onClick={handleTest}>
        Wyślij test powiadomienia
      </button>

      {message && <p className="settings-message">{message}</p>}
    </div>
  )
}
