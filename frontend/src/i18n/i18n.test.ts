import { describe, expect, it } from 'vitest'
import { LOCALES, translations, type Locale, type Translations } from './index'
import { aboutDetailDe } from './aboutDetail/de'
import { aboutDetailEn } from './aboutDetail/en'
import { aboutDetailEs } from './aboutDetail/es'
import { aboutDetailFr } from './aboutDetail/fr'
import { aboutDetailIt } from './aboutDetail/it'
import { aboutDetailPl } from './aboutDetail/pl'
import { ABOUT_TOPIC_SLUGS } from './aboutTopics'
import { resolveApiMessage } from './utils'

const aboutBundles = {
  pl: aboutDetailPl,
  en: aboutDetailEn,
  de: aboutDetailDe,
  es: aboutDetailEs,
  fr: aboutDetailFr,
  it: aboutDetailIt,
}

function collectKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([key, val]) => {
    const path = prefix ? `${prefix}.${key}` : key
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      return collectKeys(val as Record<string, unknown>, path)
    }
    return [path]
  })
}

describe('i18n completeness', () => {
  const enKeys = collectKeys(translations.en as unknown as Record<string, unknown>)

  it.each(LOCALES.filter((l) => l !== 'en'))('locale %s has same top-level keys as en', (locale: Locale) => {
    const keys = collectKeys(translations[locale] as unknown as Record<string, unknown>)
    for (const key of enKeys) {
      expect(keys, `missing ${key} in ${locale}`).toContain(key)
    }
  })

  it.each(LOCALES)('locale %s has nav, layout, api, agent sections', (locale: Locale) => {
    const t: Translations = translations[locale]
    expect(t.nav.start).toBeTruthy()
    expect(t.layout.brand).toBeTruthy()
    expect(t.api.noConnection).toBeTruthy()
    expect(t.agent.title).toBeTruthy()
  })
})

describe('aboutDetail bundles', () => {
  it.each(Object.entries(aboutBundles))('%s has all topic slugs', (locale, bundle) => {
    for (const slug of ABOUT_TOPIC_SLUGS) {
      expect(bundle.topics[slug], `${locale} missing topic ${slug}`).toBeDefined()
      expect(bundle.topics[slug].sections.length).toBeGreaterThan(0)
    }
  })

  it('locales de/fr/es/it have translated aboutDetail titles', () => {
    expect(aboutDetailDe.topics['cycles-not-headlines'].title).toMatch(/Zyklen|nicht/)
    expect(aboutDetailFr.topics['cycles-not-headlines'].title).toMatch(/cycles|Cycl/i)
    expect(aboutDetailEs.topics['cycles-not-headlines'].title).toMatch(/Ciclos|titulares/)
    expect(aboutDetailIt.topics['cycles-not-headlines'].title).toMatch(/Cicli|titoli/)
  })
})

describe('resolveApiMessage', () => {
  it('returns Polish message by default when locale is pl', () => {
    localStorage.setItem('cyclical-locale', 'pl')
    expect(resolveApiMessage('noConnection')).toContain('połączenia')
  })

  it('returns English fallback for unknown code', () => {
    expect(resolveApiMessage('noConnection', 'en')).toMatch(/connection/i)
  })

  it.each(LOCALES)('locale %s has localized noConnection (not bare code)', (locale: Locale) => {
    const msg = resolveApiMessage('noConnection', locale)
    expect(msg).not.toBe('noConnection')
    expect(msg.length).toBeGreaterThan(5)
  })
})


describe('no English copy-paste on critical growth/roi UI', () => {
  const mustDiffer: Array<{ path: string; en: string }> = [
    { path: 'growth.newsletterCta', en: translations.en.growth.newsletterCta },
    { path: 'growth.newsletterEmail', en: translations.en.growth.newsletterEmail },
    { path: 'growth.partnersHeadline', en: translations.en.growth.partnersHeadline },
    { path: 'growth.partnersLead', en: translations.en.growth.partnersLead },
    { path: 'growth.ctaBiz', en: translations.en.growth.ctaBiz },
    { path: 'growth.compliance', en: translations.en.growth.compliance },
    { path: 'growth.apiSandbox', en: translations.en.growth.apiSandbox },
    { path: 'nav.business', en: translations.en.nav.business },
    { path: 'nav.partners', en: translations.en.nav.partners },
    { path: 'roi.headline', en: translations.en.roi.headline },
    { path: 'roi.calculate', en: translations.en.roi.calculate },
    { path: 'paper.cash', en: translations.en.paper.cash },
    { path: 'logo.tagline', en: translations.en.logo.tagline },
  ]

  it.each(LOCALES.filter((l) => l !== 'en'))('%s differs from EN on critical leafs', (locale: Locale) => {
    const bundle = translations[locale]
    for (const { path, en } of mustDiffer) {
      const parts = path.split('.')
      let cur: unknown = bundle
      for (const p of parts) cur = (cur as Record<string, unknown>)[p]
      expect(cur, `${locale}.${path} still equals English`).not.toBe(en)
      expect(String(cur).length, `${locale}.${path} empty`).toBeGreaterThan(1)
    }
  })

  it('Italian Subscribe CTA is Iscriviti', () => {
    expect(translations.it.growth.newsletterCta).toBe('Iscriviti')
  })
})
