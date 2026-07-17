import { ShareMenu } from './ShareMenu'

type NewsShareMenuProps = {
  title: string
  url?: string | null
  source?: string
  compact?: boolean
}

/** @deprecated use ShareMenu — kept for macro news cards */
export function NewsShareMenu(props: NewsShareMenuProps) {
  return <ShareMenu {...props} />
}
