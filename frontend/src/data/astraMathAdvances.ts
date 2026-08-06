/** OpenAI Astra — ten advances in mathematics & TCS (Aug 2026). Educational desk. */

export type AstraAdvanceId =
  | 'spherePacking'
  | 'codes'
  | 'nonSofic'
  | 'connes'
  | 'circuits'
  | 'quantumRep'
  | 'cvp'
  | 'ehrhart'
  | 'ramsey'
  | 'extremal'

export type AstraField =
  | 'geometry'
  | 'coding'
  | 'groups'
  | 'operators'
  | 'complexity'
  | 'quantum'
  | 'crypto'
  | 'combinatorics'

export type AstraAdvance = {
  id: AstraAdvanceId
  n: number
  field: AstraField
}

export const ASTRA_SOURCE_URL = 'https://openai.com/index/ten-advances-in-mathematics/'
export const ASTRA_MANUSCRIPT_URL = 'https://cdn.openai.com/pdf/ten-proofs-oai.pdf'

export const ASTRA_ADVANCES: AstraAdvance[] = [
  { id: 'spherePacking', n: 1, field: 'geometry' },
  { id: 'codes', n: 2, field: 'coding' },
  { id: 'nonSofic', n: 3, field: 'groups' },
  { id: 'connes', n: 4, field: 'operators' },
  { id: 'circuits', n: 5, field: 'complexity' },
  { id: 'quantumRep', n: 6, field: 'quantum' },
  { id: 'cvp', n: 7, field: 'crypto' },
  { id: 'ehrhart', n: 8, field: 'geometry' },
  { id: 'ramsey', n: 9, field: 'combinatorics' },
  { id: 'extremal', n: 10, field: 'combinatorics' },
]
