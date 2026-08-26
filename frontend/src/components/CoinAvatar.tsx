import { useState } from 'react'

interface CoinAvatarProps {
  symbol: string
  name?: string
  imageUrl?: string | null
  size?: number
  className?: string
}

export function CoinAvatar({ symbol, name, imageUrl, size = 28, className = '' }: CoinAvatarProps) {
  const [broken, setBroken] = useState(false)
  const initials = (symbol || name || '?')
    .replace(/^[^A-Za-z0-9]+/, '')
    .slice(0, 2)
    .toUpperCase() || '?'

  if (imageUrl && !broken) {
    return (
      <img
        className={`coin-avatar ${className}`.trim()}
        src={imageUrl}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        decoding="async"
        onError={() => setBroken(true)}
      />
    )
  }

  return (
    <span
      className={`coin-avatar coin-avatar-fallback ${className}`.trim()}
      style={{ width: size, height: size, fontSize: Math.max(10, size * 0.38) }}
      aria-hidden
    >
      {initials}
    </span>
  )
}
