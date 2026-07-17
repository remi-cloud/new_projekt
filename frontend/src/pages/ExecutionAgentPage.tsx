import { useCallback, useEffect, useState } from 'react'
import {
  approveExecutionProposal,
  fetchExecutionProposals,
  fetchExecutionStatus,
  patchExecutionSettings,
  purgeAgentPaperPositions,
  runExecutionAgent,
} from '../api'
import { ErrorState, Loading } from '../components/Loading'
import { useLocale } from '../context/LocaleContext'
import { formatThrownError } from '../i18n/utils'
import type { ExecutionProposal, ExecutionStatus } from '../types'

const STATUS_I18N: Record<string, string> = {
  pending: 'statusPending',
  approved: 'statusApproved',
  executed: 'statusExecuted',
  dry_run: 'statusDryRun',
  skipped: 'statusSkipped',
  skipped_no_credentials: 'statusSkippedNoCredentials',
  skipped_risk: 'statusSkippedRisk',
  failed: 'statusFailed',
}

const STATUS_CLASS: Record<string, string> = {
  pending: 'exec-status-pending',
  approved: 'exec-status-approved',
  executed: 'exec-status-ok',
  dry_run: 'exec-status-dry',
  skipped: 'exec-status-skip',
  skipped_no_credentials: 'exec-status-skip',
  skipped_risk: 'exec-status-skip',
  failed: 'exec-status-fail',
}

export function ExecutionAgentPage() {
  const { t, dateLocale } = useLocale()
  const [status, setStatus] = useState<ExecutionStatus | null>(null)
  const [proposals, setProposals] = useState<ExecutionProposal[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [purging, setPurging] = useState(false)
  const [purgeMsg, setPurgeMsg] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [st, list] = await Promise.all([fetchExecutionStatus(), fetchExecutionProposals(40)])
      setStatus(st)
      setProposals(list)
    } catch (err) {
      setError(formatThrownError(err, t('execution.loadError')))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const onToggleEnabled = async () => {
    if (!status) return
    setSaving(true)
    try {
      const patch: Record<string, unknown> = { enabled: !status.enabled }
      if (!status.enabled) {
        patch.mirror_paper = false
      }
      await patchExecutionSettings(patch)
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('execution.saveError')))
    } finally {
      setSaving(false)
    }
  }

  const onPurgeAgentPositions = async () => {
    setPurging(true)
    setPurgeMsg(null)
    try {
      const data = (await purgeAgentPaperPositions()) as { purged?: string[] }
      setPurgeMsg(t('execution.purgeAgentDone', { n: data.purged?.length ?? 0 }))
    } catch (err) {
      setError(formatThrownError(err, t('api.purgeAgentFailed')))
    } finally {
      setPurging(false)
    }
  }

  const onRun = async () => {
    setRunning(true)
    try {
      await runExecutionAgent(true)
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('execution.runError')))
    } finally {
      setRunning(false)
    }
  }

  const onApprove = async (id: number) => {
    try {
      await approveExecutionProposal(id)
      await load()
    } catch (err) {
      setError(formatThrownError(err, t('execution.approveError')))
    }
  }

  if (loading && !status) return <Loading message={t('execution.loading')} />
  if (error && !status) return <ErrorState message={error} onRetry={() => void load()} />
  if (!status) return null

  return (
    <div className="execution-page">
      <header className="execution-header">
        <span className="page-eyebrow">{t('execution.eyebrow')}</span>
        <h1 className="page-title">{t('execution.title')}</h1>
        <p className="execution-lead">{t('execution.lead')}</p>
        <p className="execution-disclaimer">{t('execution.disclaimer')}</p>

        <div className="execution-status-bar">
          <span className={`execution-pill ${status.enabled ? 'on' : ''}`}>
            {status.enabled ? t('execution.enabled') : t('execution.disabled')}
          </span>
          {status.dry_run && <span className="execution-pill dry">{t('execution.dryRun')}</span>}
          {status.mirror_paper && <span className="execution-pill mirror">{t('execution.mirrorPaper')}</span>}
          <span className="execution-meta">
            {t('execution.todayCount', { n: status.proposals_today, max: status.max_daily })}
            {status.last_run_at
              ? ` · ${t('execution.lastRun', { date: new Date(status.last_run_at).toLocaleString(dateLocale) })}`
              : ''}
          </span>
        </div>

        <div className="execution-actions">
          <button
            type="button"
            className={`btn ${status.enabled ? 'btn-secondary' : 'btn-primary'} tap-target`}
            disabled={saving}
            onClick={() => void onToggleEnabled()}
          >
            {status.enabled ? t('execution.killSwitchOff') : t('execution.killSwitchOn')}
          </button>
          <button type="button" className="btn btn-secondary tap-target" disabled={running} onClick={() => void onRun()}>
            {running ? t('execution.running') : t('execution.runNow')}
          </button>
          <button
            type="button"
            className="btn btn-secondary tap-target"
            disabled={purging}
            onClick={() => void onPurgeAgentPositions()}
          >
            {purging ? t('execution.purgingAgent') : t('execution.purgeAgent')}
          </button>
        </div>
      </header>

      {purgeMsg && <p className="execution-inline-success">{purgeMsg}</p>}

      {error && <p className="execution-inline-error">{error}</p>}

      <section className="execution-brokers">
        <h2 className="section-title">{t('execution.brokersTitle')}</h2>
        <div className="execution-broker-grid">
          {status.brokers.map((b) => (
            <div key={b.broker_id} className={`execution-broker-card ${b.configured ? 'configured' : ''}`}>
              <strong>{b.name}</strong>
              <span className="execution-broker-id">{b.broker_id}</span>
              <span className={`execution-broker-state ${b.connected ? 'on' : ''}`}>
                {b.configured ? t('execution.brokerConfigured') : t('execution.brokerNotConfigured')}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="execution-proposals">
        <h2 className="section-title">{t('execution.proposalsTitle')}</h2>
        {proposals.length === 0 ? (
          <p className="empty-state">{t('execution.empty')}</p>
        ) : (
          <div className="execution-proposal-list">
            {proposals.map((p) => (
              <div key={p.id} className="execution-proposal-row">
                <div className="execution-proposal-main">
                  <strong>{p.symbol}</strong>
                  <span>{p.name}</span>
                  <span className="execution-proposal-meta">
                    {p.broker_id.toUpperCase()} · {p.source} · {p.confidence.toFixed(0)}% ·{' '}
                    {p.amount_pln.toLocaleString()} PLN
                  </span>
                </div>
                <div className="execution-proposal-side">
                  <span className={`execution-status-tag ${STATUS_CLASS[p.status] ?? ''}`}>
                    {t(`execution.${STATUS_I18N[p.status] ?? 'statusPending'}` as 'execution.statusPending')}
                  </span>
                  {p.status === 'pending' && (
                    <button type="button" className="btn btn-secondary tap-target" onClick={() => void onApprove(p.id!)}>
                      {t('execution.approve')}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
