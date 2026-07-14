import { useId } from 'react'

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
    </div>
  )
}

export function KarDigitalLogo({
  size = 44,
  showText = true,
  compact = false,
  variant = 'default',
}: KarDigitalLogoProps) {
  const uid = useId().replace(/:/g, '')
  const blueGlow = `karBlueGlow-${uid}`
  const sphereGrad = `karSphereGrad-${uid}`
  const isHero = variant === 'hero'

  return (
    <div
      className={`kar-logo ${compact ? 'kar-logo-compact' : ''} ${isHero ? 'kar-logo-hero' : ''}`}
    >
      <div className="kar-globe-mark" style={{ width: size, height: size }} aria-hidden>
        <div className="kar-scene-3d">
          {/* Pierścienie za kulą — obrót wokół osi X */}
          <div className="kar-rings-x-axis kar-rings-x-back">
            <RingDiscs />
          </div>

          {/* Kula nieruchoma — między pierścieniami */}
          <svg
            className="kar-sphere-svg"
            width={size}
            height={size}
            viewBox="0 0 64 64"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <radialGradient id={sphereGrad} cx="38%" cy="32%" r="65%">
                <stop offset="0%" stopColor="#1a3a5c" />
                <stop offset="55%" stopColor="#0a1628" />
                <stop offset="100%" stopColor="#020408" />
              </radialGradient>
              <filter id={blueGlow} x="-80%" y="-80%" width="260%" height="260%">
                <feGaussianBlur stdDeviation="1.4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <g className="kar-globe-core">
              <circle
                cx="32"
                cy="32"
                r="12"
                fill={`url(#${sphereGrad})`}
                stroke="rgba(90,200,255,0.28)"
                strokeWidth="0.9"
              />
              <ellipse
                cx="32"
                cy="32"
                rx="12"
                ry="3.8"
                stroke="rgba(90,200,255,0.14)"
                strokeWidth="0.55"
                fill="none"
              />
              <ellipse
                cx="32"
                cy="32"
                rx="12"
                ry="7.5"
                stroke="rgba(90,200,255,0.08)"
                strokeWidth="0.45"
                fill="none"
              />
              <circle className="kar-pole" cx="32" cy="19.5" r="2.8" fill="#7dd3fc" filter={`url(#${blueGlow})`} />
              <circle className="kar-pole" cx="32" cy="44.5" r="2.8" fill="#7dd3fc" filter={`url(#${blueGlow})`} />
              <text
                x="32"
                y="34.5"
                textAnchor="middle"
                className="kar-logo-glyphs"
                filter={`url(#${blueGlow})`}
              >
                KAR
              </text>
            </g>
          </svg>

          {/* Pierścienie przed kulą — ten sam obrót osi X */}
          <div className="kar-rings-x-axis kar-rings-x-front">
            <RingDiscs />
          </div>
        </div>
      </div>
      {showText && (
        <div className="kar-logo-text">
          {isHero && <span className="kar-logo-brand">KAR</span>}
          <span className="kar-logo-sub">digital</span>
          {isHero && <span className="kar-logo-tagline">Cyclical Trading Platform</span>}
        </div>
      )}
    </div>
  )
}
