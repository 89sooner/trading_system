/**
 * E2E mock setup using Playwright page.route() interception.
 *
 * We chose Playwright-native route mocking over MSW browser mode to avoid
 * Service Worker registration race conditions where the first API fetch
 * can fire before the SW is active.
 *
 * MSW is retained as a dev dependency for potential future use in
 * unit/integration tests with Node adapter (setupServer).
 */
export { setupMockRoutes } from './handlers'
