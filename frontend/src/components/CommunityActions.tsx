import { useLocale } from '../context/LocaleContext'
import type { InstrumentCommunity } from '../types'
import { communityOrFallback } from '../utils/communityLinks'

type CommunityActionsProps = {
  symbol: string
  name?: string | null
  community?: InstrumentCommunity | null
  /** Optional extra X community URL (overrides catalog). */
  xCommunityUrl?: string | null
  compact?: boolean
  className?: string
}

export function CommunityActions({
  symbol,
  name,
  community,
  xCommunityUrl,
  compact = false,
  className = '',
}: CommunityActionsProps) {
  const { t } = useLocale()
  const links = communityOrFallback(symbol, name, community)
  const communityUrl = xCommunityUrl || links.x_community || null

  const items: Array<{ key: string; href: string; label: string }> = [
    { key: 'x', href: links.x, label: t('community.x') },
  ]
  if (communityUrl) {
    items.push({ key: 'xCommunity', href: communityUrl, label: t('community.xCommunity') })
  }
  if (links.telegram) {
    items.push({ key: 'telegram', href: links.telegram, label: t('community.telegram') })
  }
  if (links.discord) {
    items.push({ key: 'discord', href: links.discord, label: t('community.discord') })
  }
  if (links.website) {
    items.push({ key: 'website', href: links.website, label: t('community.website') })
  }

  return (
    <div
      className={`community-actions card-stretch-above ${compact ? 'community-actions-compact' : ''} ${className}`.trim()}
      role="group"
      aria-label={t('community.label')}
    >
      {!compact && <span className="community-actions-label">{t('community.label')}</span>}
      {items.map((item) => (
        <a
          key={item.key}
          className="community-action-link tap-target"
          href={item.href}
          target="_blank"
          rel="noopener noreferrer"
          title={item.label}
          onClick={(e) => e.stopPropagation()}
        >
          {item.label}
        </a>
      ))}
    </div>
  )
}
