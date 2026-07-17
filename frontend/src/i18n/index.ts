import type { Locale, Translations } from './types'
import { pl } from './locales/pl'
import { de } from './locales/de'
import { en } from './locales/en'
import { fil } from './locales/fil'
import { es } from './locales/es'
import { fr } from './locales/fr'
import { it } from './locales/it'

export type { Locale, Translations }
export { DATE_LOCALE, LOCALE_STORAGE_KEY, detectLocale, interpolate, formatThrownError, resolveApiMessage } from './utils'

export const LOCALES: Locale[] = ['pl', 'de', 'en', 'fil', 'es', 'fr', 'it']

export const translations: Record<Locale, Translations> = { pl, de, en, fil, es, fr, it }

type MacroScalarKey = keyof Omit<Translations['macro'], 'tabs' | 'tabDesc' | 'category' | 'cal' | 'errors' | 'share'>

export type TranslationPath =
  | `lang.${Locale}`
  | `nav.${keyof Translations['nav']}`
  | `layout.${keyof Translations['layout']}`
  | `common.${keyof Translations['common']}`
  | `labels.asset.${keyof Translations['labels']['asset']}`
  | `labels.region.${keyof Translations['labels']['region']}`
  | `labels.signal.${keyof Translations['labels']['signal']}`
  | `labels.phase.${string}`
  | `api.${keyof Translations['api']}`
  | `macro.${MacroScalarKey}`
  | `macro.tabs.${keyof Translations['macro']['tabs']}`
  | `macro.tabDesc.${keyof Translations['macro']['tabDesc']}`
  | `macro.category.${keyof Translations['macro']['category']}`
  | `macro.share.${keyof Translations['macro']['share']}`
  | `macro.share.platforms.${keyof Translations['macro']['share']['platforms']}`
  | `macro.cal.${keyof Translations['macro']['cal']}`
  | `macro.errors.${keyof Translations['macro']['errors']}`
  | `home.${keyof Translations['home']}`
  | `investmentShowcase.${keyof Translations['investmentShowcase']}`
  | `dashboard.${keyof Translations['dashboard']}`
  | `cycles.${keyof Translations['cycles']}`
  | `opportunities.${keyof Translations['opportunities']}`
  | `markets.${keyof Translations['markets']}`
  | `instrument.${keyof Translations['instrument']}`
  | `portfolio.${keyof Translations['portfolio']}`
  | `alerts.${keyof Translations['alerts']}`
  | `about.${keyof Omit<Translations['about'], 'methodSteps' | 'chips' | 'pillars' | 'notUs'>}`
  | `banner.${keyof Translations['banner']}`
  | `paper.${keyof Translations['paper']}`
  | `chart.${keyof Translations['chart']}`
  | `confidence.${keyof Translations['confidence']}`
  | `cyclesCard.${keyof Translations['cyclesCard']}`
  | `table.${keyof Translations['table']}`
  | `orders.${keyof Translations['orders']}`
  | `positions.${keyof Translations['positions']}`
  | `markers.${keyof Translations['markers']}`
  | `logo.${keyof Translations['logo']}`
  | `broker.${keyof Translations['broker']}`
  | `pearl.${keyof Translations['pearl']}`
  | `execution.${keyof Translations['execution']}`
  | `agent.${keyof Translations['agent']}`
  | `roi.${keyof Omit<Translations['roi'], 'strategies' | 'strategyDesc' | 'errors' | 'sentiment'>}`
  | `roi.strategies.${keyof Translations['roi']['strategies']}`
  | `roi.strategyDesc.${keyof Translations['roi']['strategyDesc']}`
  | `roi.sentiment.${keyof Translations['roi']['sentiment']}`
  | `roi.errors.${keyof Translations['roi']['errors']}`
  | `growth.${keyof Omit<Translations['growth'], 'errors'>}`
  | `growth.errors.${keyof Translations['growth']['errors']}`
  | `tagTips.meaning`
  | `tagTips.suggestion`
  | `tagTips.clickHint`
  | `tagTips.layerCycle.body`
  | `tagTips.layerCycle.hint`
  | `tagTips.layerPrice.body`
  | `tagTips.layerPrice.hint`
  | `tagTips.layerMomentum.body`
  | `tagTips.layerMomentum.hint`
  | `tagTips.layerOther.body`
  | `tagTips.layerOther.hint`
  | `tagTips.momScore.body`
  | `tagTips.momScore.hint`
  | `tagTips.momPick.body`
  | `tagTips.momPick.hint`
  | `tagTips.asset.${keyof Translations['tagTips']['asset']}.body`
  | `tagTips.asset.${keyof Translations['tagTips']['asset']}.hint`
  | `tagTips.region.${keyof Translations['tagTips']['region']}.body`
  | `tagTips.region.${keyof Translations['tagTips']['region']}.hint`
  | `tagTips.phase.${keyof Translations['tagTips']['phase']}.body`
  | `tagTips.phase.${keyof Translations['tagTips']['phase']}.hint`
  | `tagTips.confidence.${keyof Translations['tagTips']['confidence']}.body`
  | `tagTips.confidence.${keyof Translations['tagTips']['confidence']}.hint`
