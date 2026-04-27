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

test('run detail page loads with run content', async ({ page }) => {
  await page.goto(`/runs/${MOCK_RUN_ID}`)
  await expect(page.getByText('Run Detail')).toBeVisible()
  await expect(page.getByText('Summary')).toBeVisible()
})
