import { SIGNAL_LABELS } from '../lib/labels'
import { SignalAction } from '../types'

export default function SignalTag({ action }: { action: SignalAction | string }) {
  const label = SIGNAL_LABELS[action as SignalAction] ?? action
  return <span className={`signal-tag signal-${action}`}>{label}</span>
}
