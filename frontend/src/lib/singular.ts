/**
 * Optional Singular Web SDK wrapper.
 * No-op when VITE_SINGULAR_SDK_KEY / SECRET / PRODUCT_ID are missing.
 */
import { SingularConfig, singularSdk } from 'singular-sdk'

const sdkKey = (import.meta.env.VITE_SINGULAR_SDK_KEY ?? '').trim()
const sdkSecret = (import.meta.env.VITE_SINGULAR_SDK_SECRET ?? '').trim()
const productId = (import.meta.env.VITE_SINGULAR_PRODUCT_ID ?? '').trim()
const productName = (import.meta.env.VITE_SINGULAR_PRODUCT_NAME ?? 'Cyclical Trader').trim()
const persistDomain = (import.meta.env.VITE_SINGULAR_PERSIST_DOMAIN ?? '').trim()

let ready = false
let initAttempted = false

export function isSingularEnabled(): boolean {
  return Boolean(sdkKey && sdkSecret && productId)
}

export function initSingular(): boolean {
  if (initAttempted) return ready
  initAttempted = true

  if (!isSingularEnabled()) {
    if (import.meta.env.DEV) {
      console.info('[singular] disabled — missing VITE_SINGULAR_* credentials')
    }
    return false
  }

  try {
    let config = new SingularConfig(sdkKey, sdkSecret, productId).withProductName(
      productName,
    )
    if (persistDomain) {
      config = config.withAutoPersistentSingularDeviceId(persistDomain)
    }
    if (import.meta.env.DEV) {
      config = config.withLogLevel(2)
    }
    singularSdk.init(config)
    ready = true
    return true
  } catch (e) {
    console.warn('[singular] init failed', e)
    ready = false
    return false
  }
}

export function trackPageVisit(): void {
  if (!ready) return
  try {
    singularSdk.pageVisit()
  } catch (e) {
    console.warn('[singular] pageVisit failed', e)
  }
}

export function trackEvent(
  name: string,
  attributes?: Record<string, string | number | boolean | null | undefined>,
): void {
  if (!ready) return
  try {
    const clean: Record<string, unknown> = {}
    if (attributes) {
      for (const [k, v] of Object.entries(attributes)) {
        if (v === undefined || v === null) continue
        clean[k] = v
      }
    }
    singularSdk.event(name, clean)
  } catch (e) {
    console.warn('[singular] event failed', e)
  }
}

/** Product events */
export const SingularEvents = {
  SCAN: 's_scan',
  POSITION_OPEN: 's_position_open',
  SUPER_LIST: 's_super_list',
  OPPORTUNITY_CLICK: 's_opportunity_click',
} as const
