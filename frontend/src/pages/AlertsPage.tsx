import { useEffect, useState } from 'react'
import {
  fetchNotificationStatus,
  saveAlertSettings,
  saveTwilioConfig,
  testNotifications,
} from '../api'
import { subscribeToPush } from '../hooks/useLiveFeed'
import { ErrorState } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import { AlertSettings, NotificationStatus, TwilioConfig } from '../types'

export function AlertsPage() {
  const { t } = useLocale()
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
      .catch(() => setError(t('alerts.loadError')))

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
      setMessage(t('alerts.saved'))
    } catch {
      setMessage(t('alerts.saveError'))
    } finally {
      setSaving(false)
    }
  }

  const handleEnablePush = async () => {
    if (!status?.vapid_public_key) {
      setMessage(t('alerts.pushUnavailable'))
      return
    }
    try {
      await subscribeToPush(status.vapid_public_key)
      setMessage(t('alerts.pushEnabled'))
      await reload()
    } catch (e) {
      setMessage(formatThrownError(e, t('alerts.pushError')))
    }
  }

  const handleSaveTwilio = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await saveTwilioConfig(twilio)
      setTwilio((prev) => ({ ...prev, auth_token: '' }))
      setMessage(t('alerts.twilioSaved'))
      await reload()
    } catch (e) {
      setMessage(formatThrownError(e, t('alerts.twilioError')))
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
        setMessage(t('alerts.testNtfy', { url: ntfy.url ?? '' }))
      } else if (sms?.ok) {
        setMessage(t('alerts.testSms', { phone: settings?.phone ?? '' }))
      } else {
        setMessage(sms?.message || t('alerts.testSent'))
      }
    } catch {
      setMessage(t('alerts.testFailed'))
    }
  }

  if (loading) return <div className="page-loading">{t('alerts.loading')}</div>
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />
  if (!settings || !status) return null

  return (
    <div className="alerts-page">
      <div className="info-banner">
        <h2>{t('alerts.title')}</h2>
        <p>{t('alerts.banner', { phone: settings.phone })}</p>
      </div>

      <section className="settings-card highlight-card">
        <h3>{t('alerts.phoneNtfyTitle')}</h3>
        <p className="settings-hint">
          {t('alerts.phoneNtfyHint1')}
          <br />
          {t('alerts.phoneNtfyHint2')}
        </p>
        <code className="topic-code">{status.ntfy_subscribe_url || settings.ntfy_topic}</code>
        {status.ntfy_app_url && (
          <a className="btn-link tap-target" href={status.ntfy_app_url}>
            {t('alerts.openNtfy')}
          </a>
        )}
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.ntfy_enabled}
            onChange={(e) => setSettings({ ...settings, ntfy_enabled: e.target.checked })}
          />
          {t('alerts.ntfyToggle')}
        </label>
      </section>

      <section className="settings-card">
        <h3>{t('alerts.smsTitle')}</h3>
        <p className="settings-hint">
          {status.sms_configured ? t('alerts.smsConfigured') : t('alerts.smsNotConfigured')}
        </p>
        <label className="field-label">
          {t('alerts.accountSid')}
          <input
            className="field-input"
            value={twilio.account_sid}
            onChange={(e) => setTwilio({ ...twilio, account_sid: e.target.value })}
            placeholder={t('alerts.placeholderSid')}
            autoComplete="off"
          />
        </label>
        <label className="field-label">
          {t('alerts.authToken')}
          <input
            className="field-input"
            type="password"
            value={twilio.auth_token}
            onChange={(e) => setTwilio({ ...twilio, auth_token: e.target.value })}
            placeholder={t('alerts.placeholderToken')}
            autoComplete="new-password"
          />
        </label>
        <label className="field-label">
          {t('alerts.fromNumber')}
          <input
            className="field-input"
            value={twilio.from_number}
            onChange={(e) => setTwilio({ ...twilio, from_number: e.target.value })}
            placeholder={t('alerts.placeholderPhone')}
          />
        </label>
        <label className="field-label">
          {t('alerts.yourNumber')}
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
          {t('alerts.smsToggle')}
        </label>
        <button type="button" className="btn-secondary tap-target" onClick={handleSaveTwilio} disabled={saving}>
          {t('alerts.saveTwilio')}
        </button>
      </section>

      <section className="settings-card">
        <h3>{t('alerts.pushTitle')}</h3>
        <p className="settings-hint">{t('alerts.pushSubscriptions', { n: status.push_subscriptions })}</p>
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={settings.push_enabled}
            onChange={(e) => setSettings({ ...settings, push_enabled: e.target.checked })}
          />
          {t('alerts.pushToggle')}
        </label>
        <button type="button" className="btn-secondary tap-target" onClick={handleEnablePush}>
          {t('alerts.enablePush')}
        </button>
      </section>

      <section className="settings-card">
        <h3>{t('alerts.thresholdsTitle')}</h3>
        <label className="field-label">
          {t('alerts.minConfidence', { n: settings.min_confidence })}
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
        {saving ? t('alerts.saving') : t('alerts.save')}
      </button>
      <button type="button" className="btn-secondary tap-target" onClick={handleTest}>
        {t('alerts.sendTest')}
      </button>

      {message && <p className="settings-message">{message}</p>}
    </div>
  )
}
