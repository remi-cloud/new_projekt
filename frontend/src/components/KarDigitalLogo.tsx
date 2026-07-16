import { useLocale } from '../context/LocaleContext'

interface KarDigitalLogoProps {
  size?: number
  showText?: boolean
  compact?: boolean
  variant?: 'default' | 'hero'
}

function RingDiscs() {
  return (
    <div className="kar-ring-discs">
      <div className="kar-ring-disc kar-ring-disc-1" />
      <div className="kar-ring-disc kar-ring-disc-2" />
      <div className="kar-ring-disc kar-ring-disc-3" />
      <div className="kar-ring-disc kar-ring-disc-4" />
      <div className="kar-ring-disc kar-ring-disc-5" />
      <div className="kar-ring-gap" aria-hidden />
    </div>
  )
}

function RingLayer({ side }: { side: 'back' | 'front' }) {
  return (
    <div className={`kar-rings-saturn kar-rings-saturn-${side}`}>
      <div className={`kar-ring-tilt kar-ring-tilt-${side}`}>
        <div className="kar-ring-spin">
          <RingDiscs />
        </div>
      </div>
    </div>
  )
}

export function KarDigitalLogo({
  size = 44,
  showText = true,
  compact = false,
  variant = 'default',
}: KarDigitalLogoProps) {
  const { t } = useLocale()
  const isHero = variant === 'hero'

  return (
    <div
      className={`kar-logo ${compact ? 'kar-logo-compact' : ''} ${isHero ? 'kar-logo-hero' : ''}`}
    >
      <div className="kar-globe-mark" style={{ width: size, height: size }} aria-hidden>
        <div className="kar-scene-3d">
          <RingLayer side="back" />

          <div className="kar-earth-globe">
            <div className="kar-earth-sphere">
              <div className="kar-earth-surface" />
              <div className="kar-earth-terminator" />
              <div className="kar-earth-specular" />
              <div className="kar-earth-limb" />
            </div>
          </div>

          <RingLayer side="front" />
        </div>
      </div>
      {showText && (
        <div className="kar-logo-text">
          {isHero && <span className="kar-logo-brand">KAR</span>}
          <span className="kar-logo-sub">digital</span>
          {isHero && <span className="kar-logo-tagline">{t('logo.tagline')}</span>}
        </div>
      )}
    </div>
  )
}
