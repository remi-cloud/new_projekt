import { Link } from 'react-router-dom'
import { ChartLoader } from './TradingChart'
import { AgentPatternChart } from './AgentPatternChart'
import {
  extractCouncilLenses,
  parseReplySections,
  type ReplySection,
} from './AgentReplyCards'

type ToolBlock = {
  tool?: string
  result?: Record<string, unknown> | null
}

function asBlocks(toolResults: unknown): ToolBlock[] {
  return Array.isArray(toolResults) ? (toolResults as ToolBlock[]) : []
}

function findResult(toolResults: unknown, tool: string, symbol?: string | null): Record<string, unknown> | null {
  for (const b of asBlocks(toolResults)) {
    if (b.tool !== tool) continue
    const r = b.result
    if (!r || typeof r !== 'object') continue
    if (symbol && typeof r.symbol === 'string' && r.symbol !== symbol) continue
    return r
  }
  return null
}

function fmtNum(v: unknown, digits = 2): string {
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: digits })
}

function biasClass(bias: string): string {
  const b = bias.toLowerCase()
  if (b.includes('bull') || b.includes('up')) return 'bull'
  if (b.includes('bear') || b.includes('down')) return 'bear'
  return 'neutral'
}

export interface DeskLabels {
  patternChart: string
  openInstrument: string
  deskBias: string
  deskLevels: string
  deskRisk: string
  analyzingSymbol: string
  deskMtf: string
  deskPatterns: string
  deskThesis: string
  deskCouncil: string
  deskSetup: string
  deskPlan: string
  deskAnalysis: string
}

interface Props {
  focusSymbol?: string | null
  toolResults?: unknown
  deskUi?: Record<string, unknown> | null
  reply?: string
  labels: DeskLabels
}

export function AgentDeskCard({ focusSymbol, toolResults, deskUi, reply, labels }: Props) {
  const desk = deskUi && typeof deskUi === 'object' ? deskUi : null
  const sym =
    (typeof desk?.symbol === 'string' && desk.symbol) ||
    focusSymbol?.trim() ||
    null

  const trend = findResult(toolResults, 'analyze_trend', sym)
  const patterns = findResult(toolResults, 'detect_patterns', sym)
  const riskTool = findResult(toolResults, 'risk_snapshot', sym)
  const mtfTool = findResult(toolResults, 'analyze_multi_timeframe', sym)

  const biasRaw = String(
    desk?.bias || (desk?.mtf as { bias?: string } | undefined)?.bias || mtfTool?.bias || trend?.trend || 'neutral',
  )
  const conviction = Number(
    desk?.conviction ?? trend?.strength ?? (desk?.mtf as { confluence_score?: number } | undefined)?.confluence_score ?? NaN,
  )
  const support = (Array.isArray(desk?.support) ? desk!.support : patterns?.support) as unknown[] | undefined
  const resistance = (Array.isArray(desk?.resistance) ? desk!.resistance : patterns?.resistance) as unknown[] | undefined
  const sList = Array.isArray(support) ? support : []
  const rList = Array.isArray(resistance) ? resistance : []

  const mtf =
    (desk?.mtf as { frames?: { range?: string; trend?: string; strength?: number; error?: string }[] } | undefined) ||
    (mtfTool as { frames?: { range?: string; trend?: string; strength?: number; error?: string }[] } | undefined)
  const frames = Array.isArray(mtf?.frames) ? mtf!.frames! : []

  const risk =
    (desk?.risk as Record<string, unknown> | undefined) ||
    (riskTool as Record<string, unknown> | undefined) ||
    {}

  const patternNames = Array.isArray(desk?.patterns)
    ? (desk!.patterns as { name?: string; confidence?: number }[])
    : []

  const sections = parseReplySections(reply || '')
  const lenses = extractCouncilLenses(sections)
  const mainSections = sections.filter((s) => s.id !== 'council' && s.id !== 'instrument')

  const sectionTitle = (s: ReplySection) => {
    if (s.id === 'thesis') return labels.deskThesis
    if (s.id === 'setup') return labels.deskSetup
    if (s.id === 'risk') return labels.deskRisk
    if (s.id === 'plan') return labels.deskPlan
    if (s.id === 'analysis') return labels.deskAnalysis
    return s.title
  }

  if (!sym && mainSections.length === 0 && lenses.length === 0) {
    return reply ? (
      <div className="agent-reply-cards">
        <article className="agent-reply-card">
          <h4>{labels.deskAnalysis}</h4>
          <p>{reply.slice(0, 900)}</p>
        </article>
      </div>
    ) : null
  }

  const convPct = Number.isFinite(conviction) ? Math.max(0, Math.min(100, Math.round(conviction))) : null
  const bc = biasClass(biasRaw)

  return (
    <div className="agent-desk agent-desk-visual">
      {sym && (
        <div className="agent-desk-head">
          <div className="agent-desk-title">
            <span className="agent-desk-symbol">{sym}</span>
            <span className={`agent-bias-pill agent-bias-${bc}`}>{biasRaw}</span>
            {convPct != null && (
              <span className="agent-desk-conv-label">
                {labels.deskBias} {convPct}%
              </span>
            )}
          </div>
          <Link className="agent-desk-link" to={`/instrument/${encodeURIComponent(sym)}`}>
            {labels.openInstrument}
          </Link>
        </div>
      )}

      {convPct != null && (
        <div className="agent-conviction" aria-hidden>
          <div className={`agent-conviction-fill agent-bias-${bc}`} style={{ width: `${convPct}%` }} />
        </div>
      )}

      {sym && (
        <p className="agent-desk-analyzing">{labels.analyzingSymbol.replace('{{symbol}}', sym)}</p>
      )}

      {sym && (
        <div className="agent-desk-chart">
          <ChartLoader symbol={sym} preset="3M" height={240} mode="candle" />
        </div>
      )}

      {(sList.length > 0 || rList.length > 0) && (
        <div className="agent-level-row">
          <span className="agent-desk-levels-label">{labels.deskLevels}</span>
          <div className="agent-level-chips">
            {sList.slice(0, 3).map((x, i) => (
              <span key={`s-${i}`} className="agent-chip agent-chip-support">
                S {fmtNum(x)}
              </span>
            ))}
            {rList.slice(0, 3).map((x, i) => (
              <span key={`r-${i}`} className="agent-chip agent-chip-resist">
                R {fmtNum(x)}
              </span>
            ))}
          </div>
        </div>
      )}

      {frames.length > 0 && (
        <div className="agent-mtf">
          <span className="agent-desk-levels-label">{labels.deskMtf}</span>
          <div className="agent-mtf-row">
            {frames.map((f, i) => {
              const t = String(f.trend || f.error || '—')
              return (
                <div key={i} className={`agent-mtf-cell agent-bias-${biasClass(t)}`}>
                  <span className="agent-mtf-range">{f.range || '—'}</span>
                  <span className="agent-mtf-trend">{t}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {patternNames.length > 0 && (
        <div className="agent-pattern-tags">
          <span className="agent-desk-levels-label">{labels.deskPatterns}</span>
          <div className="agent-level-chips">
            {patternNames.slice(0, 6).map((p, i) => (
              <span key={i} className="agent-chip agent-chip-pattern">
                {p.name}
                {typeof p.confidence === 'number' ? ` · ${Math.round(p.confidence)}%` : ''}
              </span>
            ))}
          </div>
        </div>
      )}

      {(typeof risk.summary === 'string' && risk.summary) || risk.reward_risk != null ? (
        <div className="agent-risk-strip">
          <span className="agent-desk-levels-label">{labels.deskRisk}</span>
          <div className="agent-risk-metrics">
            {risk.suggested_stop_price != null && (
              <span className="agent-chip">SL {fmtNum(risk.suggested_stop_price)}</span>
            )}
            {risk.reward_risk != null && <span className="agent-chip">R:R {fmtNum(risk.reward_risk, 2)}</span>}
            {typeof risk.summary === 'string' && <span className="agent-risk-text">{risk.summary}</span>}
          </div>
        </div>
      ) : null}

      {sym && <AgentPatternChart toolResults={toolResults} focusSymbol={sym} label={labels.patternChart} />}

      {lenses.length > 0 && (
        <div className="agent-council">
          <span className="agent-desk-levels-label">{labels.deskCouncil}</span>
          <div className="agent-council-grid">
            {lenses.map((lens) => (
              <article key={lens.id} className={`agent-council-card agent-council-${lens.id}`}>
                <h4>{lens.title}</h4>
                <p>{lens.body || '—'}</p>
              </article>
            ))}
          </div>
        </div>
      )}

      {mainSections.length > 0 && (
        <div className="agent-reply-cards">
          {mainSections
            .filter((s) => s.body.trim().length > 0)
            .slice(0, 5)
            .map((s, i) => (
              <article key={`${s.id}-${i}`} className={`agent-reply-card agent-reply-${s.id}`}>
                <h4>{sectionTitle(s)}</h4>
                <p>{s.body.slice(0, 600)}</p>
              </article>
            ))}
        </div>
      )}
    </div>
  )
}
