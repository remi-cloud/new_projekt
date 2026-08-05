import { useMemo } from 'react'

type ToolBlock = {
  tool?: string
  result?: Record<string, unknown> | null
}

function extractSvg(
  toolResults: unknown,
  focusSymbol?: string | null,
): { svg: string; symbol?: string; summary?: string } | null {
  if (!Array.isArray(toolResults)) return null
  const focus = focusSymbol?.trim() || null
  let fallback: { svg: string; symbol?: string; summary?: string } | null = null
  for (const raw of toolResults) {
    const block = raw as ToolBlock
    const res = block?.result
    if (!res || typeof res !== 'object') continue
    const svg = res.svg
    if (typeof svg !== 'string' || !svg.trimStart().startsWith('<svg')) continue
    const sym = typeof res.symbol === 'string' ? res.symbol : undefined
    const hit = {
      svg,
      symbol: sym,
      summary: typeof res.patterns_summary === 'string' ? res.patterns_summary : undefined,
    }
    if (focus && sym && sym === focus) return hit
    if (!fallback) fallback = hit
  }
  // Only use unmatched SVG when no focus filter requested
  return focus ? null : fallback
}

/** Strip scripts / event handlers from server-generated SVG before innerHTML. */
function sanitizeSvg(svg: string): string {
  let s = svg.trim()
  if (!s.startsWith('<svg')) return ''
  s = s.replace(/<script[\s\S]*?<\/script>/gi, '')
  s = s.replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
  s = s.replace(/javascript:/gi, '')
  s = s.replace(/<foreignObject[\s\S]*?<\/foreignObject>/gi, '')
  return s
}

interface Props {
  toolResults?: unknown
  focusSymbol?: string | null
  label: string
}

export function AgentPatternChart({ toolResults, focusSymbol, label }: Props) {
  const chart = useMemo(() => {
    const found = extractSvg(toolResults, focusSymbol)
    if (!found) return null
    const safe = sanitizeSvg(found.svg)
    if (!safe) return null
    return { ...found, svg: safe }
  }, [toolResults, focusSymbol])

  if (!chart) return null

  return (
    <figure className="agent-pattern-chart">
      <figcaption className="agent-pattern-chart-label">
        {label}
        {chart.symbol ? ` · ${chart.symbol}` : ''}
      </figcaption>
      <div
        className="agent-pattern-chart-svg"
        role="img"
        aria-label={chart.summary || label}
        dangerouslySetInnerHTML={{ __html: chart.svg }}
      />
    </figure>
  )
}

export function toolResultsFromMeta(meta?: Record<string, unknown> | null): unknown {
  if (!meta) return undefined
  if (Array.isArray(meta.tool_results)) return meta.tool_results
  if (Array.isArray(meta.tool_data)) return meta.tool_data
  return undefined
}

export function focusSymbolFromMeta(meta?: Record<string, unknown> | null): string | null {
  if (!meta) return null
  if (typeof meta.focus_symbol === 'string' && meta.focus_symbol.trim()) return meta.focus_symbol.trim()
  const tools = toolResultsFromMeta(meta)
  if (!Array.isArray(tools)) return null
  for (const raw of tools) {
    const r = (raw as ToolBlock)?.result
    if (r && typeof r.symbol === 'string' && r.symbol.trim()) return r.symbol.trim()
  }
  return null
}
