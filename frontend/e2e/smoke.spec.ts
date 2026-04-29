import { test, expect } from '@playwright/test'
import { setupMockRoutes, MOCK_RUN_ID } from './mocks/handlers'

test.beforeEach(async ({ page }) => {
  // Clear localStorage to prevent ApiSettingsBar/runsStore state from leaking between tests
  await page.addInitScript(() => localStorage.clear())
  await setupMockRoutes(page)
})

test('home page loads with navigation links', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('nav')).toBeVisible()
  await expect(page.locator('nav a[href="/dashboard"]')).toBeVisible()
  await expect(page.locator('nav a[href="/runs"]')).toBeVisible()
})

test('dashboard page loads with MetricCard containers', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page.getByText('Operations Console')).toBeVisible()
  await expect(page.getByText('Recent sessions')).toBeVisible()
})

test('live session history page filters and opens evidence', async ({ page }) => {
  await page.goto('/dashboard/sessions')
  await expect(page.getByText('Live Sessions')).toBeVisible()
  await page.getByLabel('Symbol').fill('005930')
  await expect(page.getByText('live-test-001')).toBeVisible()
  await page.getByText('live-test-001').click()
  await expect(page.getByText('Incident timeline')).toBeVisible()
  await expect(page.getByText('system.error')).toBeVisible()
})

test('dashboard guarded live launch sends one-share full payload', async ({ page }) => {
  let preflightPayload: Record<string, unknown> | null = null
  let startPayload: Record<string, unknown> | null = null

  await page.route('**/api/v1/live/preflight', async (route) => {
    preflightPayload = route.request().postDataJSON()
    await route.fulfill({
      json: {
        ready: true,
        reasons: [],
        blocking_reasons: [],
        warnings: [],
        quote_summary: { symbol: '005930', price: '222000', volume: '11167118' },
        quote_summaries: [{ symbol: '005930', price: '222000', volume: '11167118' }],
        symbol_count: 1,
        message: 'KIS live preflight passed.',
        checks: [
          {
            name: 'live_order_gate',
            status: 'pass',
            summary: 'Live-order environment flag is enabled for the guarded KIS route.',
            details: {
              live_execution: 'live',
              kis_env: 'prod',
              live_orders_enabled: 'true',
            },
          },
          {
            name: 'symbol_quotes',
            status: 'pass',
            summary: 'All symbols returned valid quote samples.',
            details: { symbol_count: '1' },
          },
        ],
        symbol_checks: [
          {
            symbol: '005930',
            status: 'pass',
            summary: 'Quote and sampled volume look valid.',
            price: '222000',
            volume: '11167118',
          },
        ],
        next_allowed_actions: ['paper', 'live', 'review'],
        checked_at: '2026-04-28T03:00:00Z',
      },
    })
  })

  await page.route('**/api/v1/live/runtime/start', async (route) => {
    startPayload = route.request().postDataJSON()
    await route.fulfill({
      status: 201,
      json: {
        status: 'started',
        session_id: 'live-web-001',
        state: 'starting',
        started_at: '2026-04-28T03:01:00Z',
        symbols: ['005930'],
        provider: 'kis',
        broker: 'kis',
        live_execution: 'live',
        preflight: null,
      },
    })
  })

  await page.goto('/dashboard')
  await page.getByRole('combobox', { name: 'Execution Mode' }).click()
  await page.getByRole('option', { name: 'live' }).click()

  await expect(page.getByLabel('Trade Quantity')).toHaveValue('1')
  await expect(page.getByLabel('Max Position')).toHaveValue('1')
  await expect(page.getByLabel('Max Order Size')).toHaveValue('1')

  await page.getByRole('button', { name: 'Run Preflight' }).click()
  await expect(page.getByText('Ready to proceed')).toBeVisible()

  await page.getByRole('button', { name: 'Start Runtime' }).click()
  await expect(page.getByText('Confirm guarded live launch')).toBeVisible()
  await expect(page.getByText('KIS Environment')).toBeVisible()
  await expect(page.getByText('Live Orders Flag')).toBeVisible()
  await expect(page.getByText('prod')).toBeVisible()
  await expect(page.getByText('true')).toBeVisible()

  await page.getByRole('button', { name: 'Start guarded live' }).click()
  await expect(page.getByText("Session 'live-web-001' is starting in live mode.")).toBeVisible()

  expect(preflightPayload).toMatchObject({
    mode: 'live',
    symbols: ['005930'],
    provider: 'kis',
    broker: 'kis',
    live_execution: 'live',
    risk: {
      max_position: '1',
      max_order_size: '1',
      max_notional: '300000',
    },
    backtest: {
      starting_cash: '300000',
      fee_bps: '5',
      trade_quantity: '1',
    },
  })
  expect(startPayload).toEqual(preflightPayload)
})

test('run detail page loads with run content', async ({ page }) => {
  await page.goto(`/runs/${MOCK_RUN_ID}`)
  await expect(page.getByText('Run Detail')).toBeVisible()
  await expect(page.getByText('Execution progress')).toBeVisible()
  await expect(page.getByText('worker-e2e')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible()
  await expect(page.getByText('Summary')).toBeVisible()
})
