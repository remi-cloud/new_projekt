import { useMemo } from 'react'
import { useLocale } from '../context/LocaleContext'
import {
  buildInstrumentShareTitle,
  instrumentPageUrl,
  type InstrumentShareKind,
} from '../utils/instrumentShare'
import { ShareMenu } from './ShareMenu'

type InstrumentShareMenuProps = {
  symbol: string
  name: string
  kind?: InstrumentShareKind
  signal?: string
  side?: string
  pnlPct?: number
  compact?: boolean
  className?: string
}

export function InstrumentShareMenu({
  symbol,
  name,
  kind = 'instrument',
  signal,
  side,
  pnlPct,
  compact = true,
  className,
}: InstrumentShareMenuProps) {
  const { t } = useLocale()
  const url = useMemo(() => instrumentPageUrl(symbol), [symbol])
  const title = useMemo(
    () => buildInstrumentShareTitle(kind, { name, symbol, signal, side, pnlPct }, t),
    [kind, name, symbol, signal, side, pnlPct, t],
  )

  return (
    <ShareMenu
      title={title}
      url={url}
      source="Cykliczny Trader Kar Digital"
      compact={compact}
      className={className}
    />
  )
}
