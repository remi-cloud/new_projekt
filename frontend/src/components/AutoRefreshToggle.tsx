import { useEffect, useState } from 'react'
import { useLocale } from '../context/LocaleContext'

export const AUTO_REFRESH_KEY = 'cyclical_ui_auto_refresh'
const DEFAULT_ON = true
const INTERVAL_MS = 20_000

export function isAutoRefreshEnabled(): boolean {
  try {
    const raw = localStorage.getItem(AUTO_REFRESH_KEY)
    if (raw == null) return DEFAULT_ON
    return raw === '1' || raw === 'true'
  } catch {
    return DEFAULT_ON
  }
}

export function getAutoRefreshIntervalMs(): number {
  return isAutoRefreshEnabled() ? INTERVAL_MS : 60_000
}

export function AutoRefreshToggle() {
  const { t } = useLocale()
  const [on, setOn] = useState(isAutoRefreshEnabled)

  useEffect(() => {
    try {
      localStorage.setItem(AUTO_REFRESH_KEY, on ? '1' : '0')
    } catch {
      /* ignore */
    }
    window.dispatchEvent(new CustomEvent('cyclical-auto-refresh', { detail: { on } }))
  }, [on])

  return (
    <label className="auto-refresh-toggle tap-target">
      <input type="checkbox" checked={on} onChange={(e) => setOn(e.target.checked)} />
      <span>{t('layout.autoRefresh')}</span>
    </label>
  )
}
