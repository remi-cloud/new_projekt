/** Glossary entries shown on Astra math → finance desk (ids only; copy in i18n). */
export const MATH_FINANCE_GLOSSARY = [
  'drawdown',
  'momentum',
  'rsi',
  'atr',
  'sharpe',
  'kelly',
  'correlation',
  'volatility',
  'cyclePhase',
  'confidence',
  'heatmap',
  'spread',
  'riskReward',
  'cagr',
  'beta',
] as const

export type MathFinanceGlossaryId = (typeof MATH_FINANCE_GLOSSARY)[number]
