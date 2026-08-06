import { LOCALES, useLocale } from '../context/LocaleContext'
import type { Locale } from '../i18n'

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useLocale()

  return (
    <label className={`lang-switcher ${compact ? 'lang-switcher-compact' : ''}`}>
      {!compact && <span className="lang-switcher-label">{t('layout.language')}</span>}
      <select
        className="lang-switcher-select tap-target"
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        aria-label={t('layout.language')}
      >
        {LOCALES.map((code) => (
          <option key={code} value={code}>
            {t(`lang.${code}`)}
          </option>
        ))}
      </select>
    </label>
  )
}
