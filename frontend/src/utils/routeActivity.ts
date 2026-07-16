/** Which routes need heavy background feeds (dashboard scanner, paper portfolio, SSE). */

const DASHBOARD_EXACT = new Set(['/', '/dashboard', '/rynki', '/okazje', '/cykle'])

export function needsDashboardFeed(pathname: string): boolean {
  if (DASHBOARD_EXACT.has(pathname)) return true
  if (pathname.startsWith('/instrument/')) return true
  return false
}

export function needsPortfolioFeed(pathname: string): boolean {
  if (pathname === '/portfel' || pathname.startsWith('/portfel/')) return true
  if (pathname === '/dashboard' || pathname === '/rynki' || pathname.startsWith('/rynki/')) return true
  if (pathname.startsWith('/instrument/')) return true
  return false
}

export function needsLiveSse(pathname: string): boolean {
  return (
    needsDashboardFeed(pathname) ||
    needsPortfolioFeed(pathname) ||
    pathname === '/powiadomienia' ||
    pathname.startsWith('/powiadomienia/')
  )
}
