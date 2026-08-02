import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import {
  initSingular,
  isSingularEnabled,
  SingularEvents,
  trackEvent,
  trackPageVisit,
} from '../lib/singular'

/**
 * Initializes Singular once and reports SPA page visits on route changes.
 * Init already sends the first page visit — subsequent navigations call pageVisit().
 */
export default function SingularTracker() {
  const location = useLocation()
  const first = useRef(true)
  const pathKey = `${location.pathname}${location.search}`

  useEffect(() => {
    if (!isSingularEnabled()) return
    initSingular()
  }, [])

  useEffect(() => {
    if (!isSingularEnabled()) return
    if (first.current) {
      first.current = false
      initSingular()
      // First visit is reported by singularSdk.init()
      if (location.pathname === '/superokazje') {
        trackEvent(SingularEvents.SUPER_LIST)
      }
      return
    }
    initSingular()
    trackPageVisit()
    if (location.pathname === '/superokazje') {
      trackEvent(SingularEvents.SUPER_LIST)
    }
  }, [pathKey, location.pathname])

  return null
}
