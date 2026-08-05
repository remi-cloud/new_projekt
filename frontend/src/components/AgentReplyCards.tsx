/** Parse supermind markdown reply into visual section cards. */

export type ReplySection = {
  id: string
  title: string
  body: string
}

export type CouncilLens = {
  id: 'value' | 'first' | 'liquidity'
  title: string
  body: string
}

const SECTION_ALIASES: { id: string; match: RegExp }[] = [
  { id: 'instrument', match: /instrument|bias/i },
  { id: 'thesis', match: /thesis|teza/i },
  { id: 'council', match: /council|soczew|lenses/i },
  { id: 'setup', match: /setup|układ|setup/i },
  { id: 'risk', match: /risk|ryzyk/i },
  { id: 'plan', match: /plan/i },
]

function stripMd(s: string): string {
  return s
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*/g, '')
    .replace(/^\s*[-*•]\s+/gm, '')
    .trim()
}

export function parseReplySections(reply: string): ReplySection[] {
  if (!reply.trim()) return []
  const lines = reply.replace(/\r\n/g, '\n').split('\n')
  const chunks: { title: string; body: string[] }[] = []
  let cur: { title: string; body: string[] } | null = null

  const isHeading = (line: string) => {
    const t = line.trim()
    if (/^#{1,3}\s+/.test(t)) return true
    if (/^\*\*[^*].+\*\*\s*[—:-]?/.test(t)) return true
    return false
  }

  const headingText = (line: string) =>
    stripMd(line.replace(/^#{1,3}\s+/, '').replace(/^\*\*(.+?)\*\*.*$/, '$1'))

  for (const line of lines) {
    if (isHeading(line)) {
      if (cur) chunks.push(cur)
      cur = { title: headingText(line), body: [] }
    } else if (cur) {
      cur.body.push(line)
    } else {
      cur = { title: 'Analiza', body: [line] }
    }
  }
  if (cur) chunks.push(cur)

  const sections: ReplySection[] = []
  for (const c of chunks) {
    const body = stripMd(c.body.join('\n'))
    if (!body && !c.title) continue
    let id = 'other'
    for (const a of SECTION_ALIASES) {
      if (a.match.test(c.title) || a.match.test(body.slice(0, 80))) {
        id = a.id
        break
      }
    }
    sections.push({ id, title: c.title || id, body })
  }

  if (sections.length === 0 && reply.trim()) {
    return [{ id: 'analysis', title: 'Analiza', body: stripMd(reply).slice(0, 1200) }]
  }
  return sections
}

export function extractCouncilLenses(sections: ReplySection[]): CouncilLens[] {
  const council = sections.find((s) => s.id === 'council')
  const text = council?.body || ''
  const lenses: CouncilLens[] = []
  const patterns: { id: CouncilLens['id']; re: RegExp; title: string }[] = [
    { id: 'value', re: /value\s*\/\s*capital|wartość|alokac/i, title: 'Value / Capital' },
    {
      id: 'first',
      re: /first\s*principles|asymmetr|pierwsz/i,
      title: 'First principles / Asymmetry',
    },
    { id: 'liquidity', re: /liquidity|płynność|plynnosc|power/i, title: 'Liquidity & power' },
  ]

  const parts = text.split(/\n+/).map((p) => p.trim()).filter(Boolean)
  for (const pat of patterns) {
    const hit = parts.find((p) => pat.re.test(p))
    if (hit) {
      lenses.push({
        id: pat.id,
        title: pat.title,
        body: stripMd(hit.replace(/^[^:]+:\s*/, '').replace(pat.re, '').replace(/^[:\s—-]+/, '') || hit),
      })
    }
  }

  // Fallback: split council body into up to 3 chunks
  if (lenses.length === 0 && text) {
    const chunks = parts.slice(0, 3)
    const titles = ['Value / Capital', 'First principles / Asymmetry', 'Liquidity & power'] as const
    const ids: CouncilLens['id'][] = ['value', 'first', 'liquidity']
    chunks.forEach((c, i) => {
      lenses.push({ id: ids[i], title: titles[i], body: stripMd(c) })
    })
  }
  return lenses
}
