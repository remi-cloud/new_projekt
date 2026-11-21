import { useEffect, useState } from 'react'
import { deskSessionOpen } from '../lib/deskAuth'

/** True when a desk session is open. Guests (no token) get false, so callers
 * can hide or disable state-changing controls instead of firing a 401. */
export function useDeskSession(): boolean {
  const [authed, setAuthed] = useState(false)
  useEffect(() => {
    let alive = true
    const sync = () => {
      void deskSessionOpen().then((open) => {
        if (alive) setAuthed(open)
      })
    }
    sync()
    window.addEventListener('desk-auth', sync)
    return () => {
      alive = false
      window.removeEventListener('desk-auth', sync)
    }
  }, [])
  return authed
}
