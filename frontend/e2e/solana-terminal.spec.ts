import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

test('solana terminal renders and screenshots', async ({ page }, info) => {
  await page.goto('/solana')
  const terminal = page.getByTestId('gbt-terminal')
  await expect(terminal).toBeVisible()
  await expect(terminal.locator('.gbt-title strong')).toHaveText('Grok Bot')
  await expect(terminal.locator('.gbt-title span')).toHaveText('Terminal')
  await expect(page.getByTestId('gbt-footer')).toHaveText(/paper · real quotes|LIVE · on-chain/)
  await expect(page.getByText(/illustrative/i)).toHaveCount(0)
  const out = path.resolve('test-results/solana-terminal')
  fs.mkdirSync(out, { recursive: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.screenshot({ path: path.join(out, `${info.project.name}-1440x900.png`), fullPage: true })
  await page.setViewportSize({ width: 1080, height: 1350 })
  await page.screenshot({ path: path.join(out, `${info.project.name}-1080x1350.png`), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(terminal.getByText('AGENTS', { exact: true })).toBeVisible()
})
