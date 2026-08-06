import { formatSignal, signalDirection } from '../lib/labels'

export default function SignalTag({ action }: { action: string }) {
  const dir = signalDirection(action)
  return <span className={`signal-tag signal-${dir}`}>{formatSignal(action)}</span>
}
