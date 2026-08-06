export const ABOUT_PILLAR_SLUGS = [
  'cycles-not-headlines',
  'own-schemas',
  'long-term-horizon',
  'terminal-not-tabloid',
] as const

export const ABOUT_NOT_SLUGS = [
  'not-breaking-news',
  'not-headline-trading',
  'not-minute-signals',
] as const

export const ABOUT_METHOD_SLUGS = [
  'method-map-cycles',
  'method-layers',
  'method-discipline',
  'method-years',
] as const

export const ABOUT_TOPIC_SLUGS = [
  ...ABOUT_PILLAR_SLUGS,
  ...ABOUT_NOT_SLUGS,
  ...ABOUT_METHOD_SLUGS,
] as const

export type AboutTopicSlug = (typeof ABOUT_TOPIC_SLUGS)[number]

export function isAboutTopicSlug(value: string): value is AboutTopicSlug {
  return (ABOUT_TOPIC_SLUGS as readonly string[]).includes(value)
}

export function aboutTopicPath(slug: AboutTopicSlug): string {
  return `/o-nas/${slug}`
}
