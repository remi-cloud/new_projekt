/** Seed Finance Agent chat and navigate to /agent */

export const AGENT_SEED_KEY = 'cyclical_agent_seed'
/** @deprecated kept for ROI page backward compat — reader checks both */
export const ROI_AGENT_SEED_KEY = 'cyclical_agent_roi_seed'

export type AgentSeed = {
  message: string
  symbol?: string
}

export function seedAgentChat(seed: AgentSeed): void {
  const payload = JSON.stringify({
    message: seed.message.trim(),
    symbol: seed.symbol?.trim() || undefined,
  })
  sessionStorage.setItem(AGENT_SEED_KEY, payload)
  // Keep legacy key in sync for any old readers
  sessionStorage.setItem(ROI_AGENT_SEED_KEY, payload)
}

export function consumeAgentSeed(): AgentSeed | null {
  const raw = sessionStorage.getItem(AGENT_SEED_KEY) || sessionStorage.getItem(ROI_AGENT_SEED_KEY)
  if (!raw) return null
  sessionStorage.removeItem(AGENT_SEED_KEY)
  sessionStorage.removeItem(ROI_AGENT_SEED_KEY)
  try {
    const seed = JSON.parse(raw) as AgentSeed
    if (!seed.message?.trim()) return null
    return {
      message: seed.message.trim(),
      symbol: seed.symbol?.trim() || undefined,
    }
  } catch {
    return null
  }
}

export function newsAnalysisPrompt(
  locale: string,
  item: { title: string; summary?: string | null; source?: string | null; url?: string | null; category?: string | null },
): string {
  const title = item.title.trim()
  const summary = (item.summary || '').trim()
  const source = (item.source || '').trim()
  const url = (item.url || '').trim()
  const cat = (item.category || '').trim()
  if (locale === 'pl') {
    return [
      `Przeanalizuj ten news dla desk tradingowego:`,
      `Tytuł: ${title}`,
      cat ? `Kategoria: ${cat}` : '',
      source ? `Źródło: ${source}` : '',
      summary ? `Streszczenie: ${summary.slice(0, 500)}` : '',
      url ? `Link: ${url}` : '',
      `Oceń: wpływ na ryzyko (risk-on/off), Fed/USD/BTC jeśli dotyczy, bias Trump/Musk/stagflacja gdy pasuje, oraz konkretny wniosek dla traderów. Krótko i konkretnie.`,
    ]
      .filter(Boolean)
      .join('\n')
  }
  return [
    `Analyze this news for a trading desk:`,
    `Title: ${title}`,
    cat ? `Category: ${cat}` : '',
    source ? `Source: ${source}` : '',
    summary ? `Summary: ${summary.slice(0, 500)}` : '',
    url ? `Link: ${url}` : '',
    `Assess: risk-on/off impact, Fed/USD/BTC if relevant, Trump/Musk/stagflation bias when it fits, and a concrete takeaway for traders. Keep it short.`,
  ]
    .filter(Boolean)
    .join('\n')
}

export function instrumentAnalysisPrompt(locale: string, symbol: string, name?: string): string {
  const label = name ? `${name} (${symbol})` : symbol
  if (locale === 'pl') {
    return `Pełna analiza instrumentu ${label}: trend, wzorce, cykl (BTC/prezydencki jeśli pasuje), ryzyko i konkretny bias. Informacja edukacyjna.`
  }
  return `Full analysis of ${label}: trend, patterns, cycle (BTC/presidential if relevant), risk and concrete bias. Educational only.`
}
