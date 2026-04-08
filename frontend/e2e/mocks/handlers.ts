import type { Page } from '@playwright/test'
import type {
  DashboardStatus,
  PositionsResponse,
  EventFeed,
  BacktestRunStatusDTO,
  TradeAnalyticsResponse,
  StrategyProfileDTO,
} from '../../lib/api/types'

// ── Fixture data ──

export const dashboardStatus: DashboardStatus = {
  state: 'running',
  last_heartbeat: '2026-04-07T12:00:00Z',
  uptime_seconds: 3600,
  provider: 'kis',
  symbols: ['005930', '000660'],
  market_session: 'regular',
  last_reconciliation_at: '2026-04-07T11:00:00Z',
  last_reconciliation_status: 'ok',
}

export const dashboardPositions: PositionsResponse = {
  positions: [
    {
      symbol: '005930',
      quantity: '10',
      average_cost: '70000',
      unrealized_pnl: '5000',
    },
  ],
  cash: '1000000',
}

export const dashboardEvents: EventFeed = {
  events: [
    {
      event: 'order_filled',
      severity: 'info',
      correlation_id: 'corr-001',
      timestamp: '2026-04-07T11:30:00Z',
      payload: { symbol: '005930', side: 'buy', quantity: 10 },
    },
  ],
  total: 1,
}

export const MOCK_RUN_ID = 'run-test-001'

export const backtestRunDetail: BacktestRunStatusDTO = {
  run_id: MOCK_RUN_ID,
  status: 'succeeded',
  started_at: '2026-04-07T10:00:00Z',
  finished_at: '2026-04-07T10:05:00Z',
  input_symbols: ['005930'],
  mode: 'backtest',
  result: {
    summary: {
      return: '0.05',
      max_drawdown: '0.02',
      volatility: '0.15',
      win_rate: '0.6',
    },
    equity_curve: [
      { timestamp: '2026-04-01T09:00:00Z', equity: '1000000' },
      { timestamp: '2026-04-02T09:00:00Z', equity: '1010000' },
      { timestamp: '2026-04-03T09:00:00Z', equity: '1050000' },
    ],
    drawdown_curve: [
      { timestamp: '2026-04-01T09:00:00Z', drawdown: '0' },
      { timestamp: '2026-04-02T09:00:00Z', drawdown: '0.005' },
      { timestamp: '2026-04-03T09:00:00Z', drawdown: '0' },
    ],
    signals: [],
    orders: [],
    risk_rejections: [],
  },
}

export const tradeAnalytics: TradeAnalyticsResponse = {
  stats: {
    trade_count: 5,
    win_rate: '0.6',
    risk_reward_ratio: '1.5',
    max_drawdown: '0.02',
    average_time_in_market_seconds: 300,
  },
  trades: [
    {
      symbol: '005930',
      entry_time: '2026-04-01T09:30:00Z',
      exit_time: '2026-04-01T10:00:00Z',
      entry_price: '70000',
      exit_price: '71000',
      quantity: '10',
      pnl: '10000',
      holding_seconds: 1800,
    },
  ],
}

export const strategyProfiles: StrategyProfileDTO[] = [
  {
    strategy_id: 'strat-001',
    name: 'Test Strategy',
    strategy: { type: 'pattern_signal' },
  },
]

// ── Playwright route-based mock setup ──

/**
 * Register API mock handlers using Playwright's page.route().
 * This avoids MSW Service Worker registration race conditions.
 */
export async function setupMockRoutes(page: Page) {
  await page.route('**/api/v1/dashboard/status', (route) =>
    route.fulfill({ json: dashboardStatus }),
  )

  await page.route('**/api/v1/dashboard/positions', (route) =>
    route.fulfill({ json: dashboardPositions }),
  )

  await page.route('**/api/v1/dashboard/events**', (route) =>
    route.fulfill({ json: dashboardEvents }),
  )

  await page.route('**/api/v1/backtests/*', (route) =>
    route.fulfill({ json: backtestRunDetail }),
  )

  await page.route('**/api/v1/analytics/backtests/*/trades', (route) =>
    route.fulfill({ json: tradeAnalytics }),
  )

  await page.route('**/api/v1/strategies**', (route) =>
    route.fulfill({ json: strategyProfiles }),
  )
}
