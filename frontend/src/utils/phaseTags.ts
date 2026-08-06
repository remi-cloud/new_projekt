/** CSS class for price/momentum phase tags (bearish vs bullish). */

const BEARISH_PHASES = new Set([
  'bear',
  'distribution',
  'silne_spadk',
  'spadek',
  'year_4',
])

const BULLISH_PHASES = new Set([
  'bull',
  'accumulation',
  'silne_wzrost',
  'wzrost',
  'year_1',
  'year_2',
])

export function phaseTagClass(phase: string | null | undefined): string {
  if (!phase) return 'phase-neutral'
  if (BEARISH_PHASES.has(phase)) return 'phase-bearish'
  if (BULLISH_PHASES.has(phase)) return 'phase-bullish'
  return 'phase-neutral'
}

export function confidenceTier(confidence: number): 'high' | 'mid' | 'low' {
  if (confidence >= 80) return 'high'
  if (confidence >= 60) return 'mid'
  return 'low'
}
