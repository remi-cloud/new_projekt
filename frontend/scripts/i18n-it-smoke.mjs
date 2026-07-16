/**
 * Smoke: Italian Partners page must show Iscriviti, not Subscribe.
 * Usage: node scripts/i18n-it-smoke.mjs
 */
import { spawn } from 'child_process'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const WebSocket = require('ws')

const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const userData = `/tmp/chrome-i18n-it-${Date.now()}`
const port = 9341
const base = 'http://127.0.0.1:8080'

const proc = spawn(
  chrome,
  [
    '--headless=new',
    '--disable-gpu',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userData}`,
    '--no-first-run',
    '--disable-extensions',
    '--window-size=1440,900',
    'about:blank',
  ],
  { stdio: 'ignore' },
)

await new Promise((r) => setTimeout(r, 1800))

async function waitForTabs() {
  for (let i = 0; i < 25; i++) {
    try {
      const tabs = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json())
      const page = tabs.find((t) => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 250))
  }
  throw new Error('no page')
}

const tab = await waitForTabs()
const ws = new WebSocket(tab.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const msgId = ++id
    pending.set(msgId, { resolve, reject })
    ws.send(JSON.stringify({ id: msgId, method, params }))
    setTimeout(() => {
      if (pending.has(msgId)) {
        pending.delete(msgId)
        reject(new Error(`timeout ${method}`))
      }
    }, 25000)
  })

ws.on('message', (data) => {
  const msg = JSON.parse(data.toString())
  if (msg.id && pending.has(msg.id)) {
    const { resolve } = pending.get(msg.id)
    pending.delete(msg.id)
    resolve(msg)
  }
})

await new Promise((resolve, reject) => {
  ws.on('open', resolve)
  ws.on('error', reject)
})

await send('Page.enable')
await send('Runtime.enable')
await send('Network.enable')
await send('Network.setCacheDisabled', { cacheDisabled: true })

await send('Page.navigate', { url: base })
await new Promise((r) => setTimeout(r, 1500))

await send('Runtime.evaluate', {
  expression: `localStorage.setItem('cyclical-locale','it'); location.href='${base}/partnerzy';`,
})
await new Promise((r) => setTimeout(r, 2500))

const result = await send('Runtime.evaluate', {
  expression: `({
    text: document.body.innerText,
    html: document.documentElement.lang,
    hasIscriviti: document.body.innerText.includes('Iscriviti'),
    hasSubscribe: /\\bSUBSCRIBE\\b|\\bSubscribe\\b/.test(document.body.innerText),
    hasCollaborazioni: document.body.innerText.includes('Collaborazioni'),
    hasPartnerships: document.body.innerText.includes('PARTNERSHIPS') || document.body.innerText.includes('Partnerships'),
    snippet: document.body.innerText.slice(0, 800)
  })`,
  returnByValue: true,
})

const v = result.result?.result?.value
console.log(JSON.stringify(v, null, 2))

proc.kill('SIGKILL')

if (!v?.hasIscriviti || v?.hasSubscribe || !v?.hasCollaborazioni) {
  console.error('FAIL: Italian Partners page still showing English growth copy')
  process.exit(1)
}
console.log('OK: Italian Partners i18n looks correct')
