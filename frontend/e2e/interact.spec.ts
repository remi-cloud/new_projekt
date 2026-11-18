import { expect, test, type Page } from '@playwright/test'
import fs from 'node:fs'

const TOKEN = 'e2e-desk'
const ROUTES = [
  '/',
  '/dashboard',
  '/ai-hacking',
  '/radar',
  '/okazje',
  '/superokazje',
  '/superokazje/NG%3DF',
  '/pozycja/BTC-USD',
  '/rynki',
  '/perly',
  '/fomo',
  '/axiom',
  '/launch',
  '/cykle',
  '/kalkulator',
  '/news',
  '/live',
  '/agent',
  '/narzedzia',
  '/narzedzia/singularity',
  '/narzedzia/astra',
  '/execution',
  '/portfel',
  '/powiadomienia',
  '/biznes',
  '/partnerzy',
  '/o-nas',
  '/logowanie',
]

type Issue = { route: string; auth: string; viewport: string; kind: string; detail: string }
const issues: Issue[] = []

function note(page: Page, auth: string, kind: string, detail: string) {
  const viewport = page.viewportSize()
  issues.push({
    route: (() => {
      try { return new URL(page.url()).pathname } catch { return '?' }
    })(),
    auth,
    viewport: viewport ? String(viewport.width) : '?',
    kind,
    detail: detail.slice(0, 220),
  })
}

function arm(page: Page, auth: string) {
  page.on('pageerror', (error) => note(page, auth, 'pageerror', String(error)))
  page.on('console', (msg) => {
    const text = msg.text()
    if (/content security policy|violates the following/i.test(text)) note(page, auth, 'csp', text)
    if (msg.type() !== 'error') return
    if (/favicon|ERR_BLOCKED_BY_CLIENT/i.test(text)) return
    // The response listener has the URL. A bare "failed to load" line does not.
    if (/Failed to load resource/i.test(text)) return
    note(page, auth, 'console', text)
  })
  page.on('response', (res) => {
    const url = res.url()
    if (!url.includes('/api/')) return
    const status = res.status()
    const guestClosed = auth === 'anon' && status === 401 && !['/api/roi/calculate', '/api/growth/', '/api/ai/chat', '/api/news/macro/refresh'].some((path) => url.includes(path))
    const expected =
      guestClosed ||
      (status === 401 && (url.includes('/social/posts') || url.includes('/social/decisions') || url.includes('/desk/login'))) ||
      (status === 409 && url.includes('/social/posts/') && url.includes('/publish')) ||
      (status === 503 && (url.includes('/api/dashboard') || url.includes('/api/ai/chat')))
    if ((status === 400 || status === 401 || status === 409 || status === 503 || status >= 500) && !expected) {
      note(page, auth, 'http', `${status} ${url}`)
    }
  })
}

async function login(page: Page) {
  await page.goto('/logowanie')
  await page.locator('#desk-token').fill(TOKEN)
  await page.getByRole('button', { name: /wejdź/i }).click()
  await expect(page.getByText(/zalogowano/i)).toBeVisible()
}

async function walk(page: Page, auth: string) {
  for (const route of ROUTES) {
    await page.goto(route, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(250)
    const text = (await page.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ')
    if (/nav\.[a-zA-Z]|layout\.[a-zA-Z]|superDesk\.[a-zA-Z]|radarPage\.[a-zA-Z]/.test(text)) {
      note(page, auth, 'i18n-key', text.slice(0, 160))
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    if (overflow > 24) note(page, auth, 'overflow', String(overflow))

    const controls = page.locator('#app-content button:visible, #app-content [role="tab"]:visible')
    const total = Math.min(await controls.count(), 6)
    for (let i = 0; i < total; i += 1) {
      const control = controls.nth(i)
      const label = ((await control.innerText().catch(() => '')) || '').trim()
      if (!label || /reset|wyczyść|purge|usuń wszystkie|github|ic3|cert|wejdź|zapisz|wyślij|publikuj|subskryb/i.test(label)) continue
      const urlBefore = page.url()
      await control.scrollIntoViewIfNeeded().catch(() => undefined)
      await control.click({ timeout: 700 }).catch(() => undefined)
      await page.waitForTimeout(80)
      if (!page.url().startsWith(urlBefore.split('?')[0]) && !page.url().includes(new URL(urlBefore).pathname)) {
        await page.goto(route, { waitUntil: 'domcontentloaded' }).catch(() => undefined)
      }
    }
    const map = page.getByRole('button', { name: /mapę 3d/i })
    if (await map.count()) await map.first().click({ timeout: 800 }).catch(() => undefined)
  }
}

test.afterAll(() => {
  fs.mkdirSync('e2e-report', { recursive: true })
  fs.writeFileSync('e2e-report/issues.json', JSON.stringify(issues, null, 2))
})

for (const auth of ['anon', 'token'] as const) {
  test(`interakcje ${auth}`, async ({ page }) => {
    test.setTimeout(240_000)
    arm(page, auth)
    if (auth === 'token') await login(page)
    await walk(page, auth)
    const hard = issues.filter((item) => item.auth === auth && ['pageerror', 'csp', 'i18n-key', 'overflow', 'http', 'console'].includes(item.kind))
    expect(hard, JSON.stringify(hard.slice(0, 20), null, 2)).toEqual([])
  })
}
