import { useMemo } from 'react'
import { useLocale } from '../context/LocaleContext'
import type { TranslationPath } from './index'

export function useDomainLabels() {
  const { t } = useLocale()

  return useMemo(
    () => ({
      asset: {
        crypto: t('labels.asset.crypto'),
        stock: t('labels.asset.stock'),
        etf: t('labels.asset.etf'),
        index: t('labels.asset.index'),
        bond: t('labels.asset.bond'),
        commodity: t('labels.asset.commodity'),
        forex: t('labels.asset.forex'),
      },
      region: {
        global: t('labels.region.global'),
        us: t('labels.region.us'),
        eu: t('labels.region.eu'),
        asia: t('labels.region.asia'),
        em: t('labels.region.em'),
        pl: t('labels.region.pl'),
      },
      signal: {
        buy: t('labels.signal.buy'),
        sell: t('labels.signal.sell'),
        hold: t('labels.signal.hold'),
        watch: t('labels.signal.watch'),
      },
      phase: (key: string): string => {
        const path = `labels.phase.${key}` as TranslationPath
        const val = t(path)
        return val === path ? key : val
      },
    }),
    [t],
  )
}
