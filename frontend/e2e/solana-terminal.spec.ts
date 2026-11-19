import { expect, test } from '@playwright/test'
import path from 'node:path'

test('solana terminal renders and screenshots', async ({ page }, info) => {
  await page.goto('/solana')
  await expect(page.getByText('Grok Bot')).toBeVisible()
  await expect(page.getByText('Terminal')).toBeVisible()
  await expect(page.getByTestId('gbt-footer')).toBeVisible()
  await expect(page.getByText(/illustrative/i)).toHaveCount(0)
  const wide = path.resolve('/opt/cursor/artifacts', `solana-terminal-${info.project.name}-1440x900.png`)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.screenshot({ path: wide, fullPage: true })
  const tall = path.resolve('/opt/cursor/artifacts', `solana-terminal-${info.project.name}-1080x1350.png`)
  await page.setViewportSize({ width: 1080, height: 1350 })
  await page.screenshot({ path: tall, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByText('AGENTS')).toBeVisible()
})
