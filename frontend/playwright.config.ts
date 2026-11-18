import { defineConfig, devices } from '@playwright/test'

const port = process.env.E2E_PORT || '8091'
const python = process.env.E2E_PYTHON || 'python3'

export default defineConfig({
  testDir: './e2e',
  timeout: 180_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: 'retain-on-failure',
    locale: 'pl-PL',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, isMobile: true } },
  ],
  webServer: {
    command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port ${port}`,
    cwd: '../backend',
    url: `http://127.0.0.1:${port}/api/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      CYCLICAL_APP_ENV: 'production',
      CYCLICAL_DESK_TOKEN: 'e2e-desk',
      CYCLICAL_SOCIAL_DRY_RUN: 'true',
      CYCLICAL_SOCIAL_AUTO_POST: 'false',
      CYCLICAL_BINANCE_AI_BOT_DRY_RUN: 'true',
      CYCLICAL_DATABASE_PATH: '/tmp/e2e-trader.db',
      CYCLICAL_PORTFOLIO_DATABASE_PATH: '/tmp/e2e-portfolio/portfolio.db',
      CYCLICAL_PORTFOLIO_RESTORE_BACKUP: 'false',
      CYCLICAL_PORTFOLIO_MIGRATE_LEGACY: 'false',
      CYCLICAL_AUTO_BACKUP_ENABLED: 'false',
      CYCLICAL_PEARL_HUNTER_ENABLED: 'false',
    },
  },
})
