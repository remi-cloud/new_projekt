import { useEffect, useRef, useState } from 'react'
import { API_BASE } from '../api'

export interface LiveEvent {
  type: string
  data?: unknown
  at?: string
}

export function useLiveFeed(onEvent?: (event: LiveEvent) => void) {
  const [connected, setConnected] = useState(false)
  const [lastEventAt, setLastEventAt] = useState<string | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    let es: EventSource | null = null
    let retryMs = 3000

    const connect = () => {
      es = new EventSource(`${API_BASE}/live/stream`)
      es.onopen = () => {
        setConnected(true)
        retryMs = 3000
      }
      es.onmessage = (msg) => {
        try {
          const parsed = JSON.parse(msg.data) as LiveEvent
          if (parsed.at) setLastEventAt(parsed.at)
          else if (parsed.type !== 'heartbeat') setLastEventAt(new Date().toISOString())
          onEventRef.current?.(parsed)
        } catch {
          /* ignore */
        }
      }
      es.onerror = () => {
        setConnected(false)
        es?.close()
        setTimeout(connect, retryMs)
        retryMs = Math.min(retryMs * 1.5, 30000)
      }
    }

    connect()
    return () => es?.close()
  }, [])

  return { connected, lastEventAt }
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

export async function subscribeToPush(vapidPublicKey: string): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Push nie jest wspierany w tej przeglądarce')
  }
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error('Brak zgody na powiadomienia')
  }
  const reg = await navigator.serviceWorker.register('/sw.js')
  await navigator.serviceWorker.ready
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  })
  const json = sub.toJSON()
  const res = await fetch(`${API_BASE}/notifications/push/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint: json.endpoint, keys: json.keys }),
  })
  if (!res.ok) throw new Error('Nie udało się zapisać subskrypcji')
  return true
}
