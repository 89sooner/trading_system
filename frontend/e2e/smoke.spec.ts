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
  await expect(page.getByText('Live Dashboard')).toBeVisible()
  await expect(page.locator('[data-slot="card"]').first()).toBeVisible()
})

test('run detail page loads with run content', async ({ page }) => {
  await page.goto(`/runs/${MOCK_RUN_ID}`)
  await expect(page.getByText('Run Detail')).toBeVisible()
  await expect(page.getByText('Summary')).toBeVisible()
})
