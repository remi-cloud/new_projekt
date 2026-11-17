import { FormEvent, useEffect, useState } from 'react'
import { apiFetch, clearDeskToken, writeDeskToken } from '../lib/deskAuth'
import { API_BASE } from '../lib/sameOrigin'
import { useLocale } from '../context/LocaleContext'

export function DeskLoginPage() {
  const { t } = useLocale()
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [token, setToken] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let alive = true
    apiFetch(`${API_BASE}/desk/status`)
      .then((res) => (res.ok ? res.json() : { configured: false }))
      .then((body: { configured?: boolean }) => {
        if (alive) setConfigured(Boolean(body.configured))
      })
      .catch(() => {
        if (alive) setConfigured(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setMessage('')
    const res = await apiFetch(`${API_BASE}/desk/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    if (res.status === 403) {
      setConfigured(false)
      clearDeskToken()
      setMessage(t('layout.loginClosed'))
      return
    }
    if (!res.ok) {
      clearDeskToken()
      setMessage(t('layout.loginBad'))
      return
    }
    writeDeskToken(token)
    setToken('')
    setMessage(t('layout.loginOk'))
  }

  return (
    <div className="institutional-page desk-login-page">
      <header className="page-intro">
        <h2 className="page-headline">{t('layout.loginTitle')}</h2>
        <p className="page-lead">{t('layout.loginLead')}</p>
      </header>
      {configured === false && <p className="desk-login-closed">{t('layout.loginClosed')}</p>}
      {configured !== false && (
        <form className="desk-login-form" onSubmit={onSubmit}>
          <label className="field-label" htmlFor="desk-token">
            {t('layout.loginToken')}
            <input
              id="desk-token"
              className="field-input"
              type="password"
              autoComplete="current-password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <button className="btn btn-primary" type="submit">
            {t('layout.loginSubmit')}
          </button>
        </form>
      )}
      {message && <p className="desk-login-message">{message}</p>}
    </div>
  )
}
