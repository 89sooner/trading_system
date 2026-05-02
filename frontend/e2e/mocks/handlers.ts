import type { Page } from '@playwright/test'
import type {
  DashboardStatus,
  PositionsResponse,
  EventFeed,
  LiveOrderList,
  BacktestRunStatusDTO,
  TradeAnalyticsResponse,
  StrategyProfileDTO,
  LiveRuntimeSessionList,
  EquityTimeseriesResponse,
  LiveRuntimeSessionEvidence,
} from '../../lib/api/types'

// ── Fixture data ──

export const dashboardStatus: DashboardStatus = {
  state: 'running',
  last_heartbeat: '2026-04-07T12:00:00Z',
  uptime_seconds: 3600,
  active: false,
  controller_state: 'idle',
  session_id: null,
  live_execution: 'live',
  provider: 'kis',
  broker: 'kis',
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

export const dashboardOrders: LiveOrderList = {
  orders: [
    {
      record_id: 'live-order-001',
      session_id: 'live-test-001',
      symbol: '005930',
      side: 'buy',
      requested_quantity: '3',
      filled_quantity: '1',
      remaining_quantity: '2',
      status: 'partially_filled',
      broker_order_id: '90001',
      submitted_at: '2026-04-07T10:30:00Z',
      last_synced_at: '2026-04-07T10:31:00Z',
      stale_after: '2026-04-07T10:35:00Z',
      cancel_requested: false,
      payload: {},
    },
  ],
  total: 1,
}

export const dashboardEquity: EquityTimeseriesResponse = {
  session_id: 'live-test-001',
  points: [],
  total: 0,
}

export const liveRuntimeSessions: LiveRuntimeSessionList = {
  sessions: [
    {
      session_id: 'live-test-001',
      started_at: '2026-04-07T10:00:00Z',
      ended_at: '2026-04-07T11:00:00Z',
      provider: 'kis',
      broker: 'kis',
      live_execution: 'paper',
      symbols: ['005930'],
      last_state: 'stopped',
      last_error: null,
      preflight_summary: {
        checked_at: '2026-04-07T09:59:00Z',
        ready: true,
        message: 'Ready',
        blocking_reasons: [],
        warnings: [],
        next_allowed_actions: ['paper'],
      },
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
}

export const liveRuntimeSessionEvidence: LiveRuntimeSessionEvidence = {
  session: liveRuntimeSessions.sessions[0],
  order_audit_count: 1,
  recent_order_audit_records: [
    {
      record_id: 'audit-001',
      scope: 'live_session',
      owner_id: 'live-test-001',
      event: 'order.filled',
      symbol: '005930',
      side: 'buy',
      requested_quantity: '1',
      filled_quantity: '1',
      price: '70000',
      status: 'filled',
      reason: null,
      timestamp: '2026-04-07T10:10:00Z',
      payload: {},
      broker_order_id: 'broker-001',
    },
  ],
  live_order_count: 1,
  recent_live_orders: dashboardOrders.orders,
  equity_point_count: 2,
  archived_event_count: 1,
  recent_archived_events: [
    {
      record_id: 'event-001',
      session_id: 'live-test-001',
      event: 'system.error',
      severity: 'ERROR',
      correlation_id: 'cid-001',
      timestamp: '2026-04-07T10:20:00Z',
      payload: { reason: 'simulated warning' },
    },
  ],
}

export const MOCK_RUN_ID = 'run-test-001'

export const backtestRunDetail: BacktestRunStatusDTO = {
  run_id: MOCK_RUN_ID,
  status: 'succeeded',
  started_at: '2026-04-07T10:00:00Z',
  finished_at: '2026-04-07T10:05:00Z',
  input_symbols: ['005930'],
  mode: 'backtest',
  job: {
    worker_id: 'worker-e2e',
    lease_expires_at: '2026-04-07T10:06:00Z',
    last_heartbeat_at: '2026-04-07T10:04:00Z',
    attempt_count: 1,
    max_attempts: 3,
    cancel_requested: false,
    progress: {
      processed_bars: 42,
      total_bars: 42,
      percent: 100,
      last_bar_timestamp: '2026-04-03T09:00:00Z',
      updated_at: '2026-04-07T10:04:00Z',
    },
  },
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

  await page.route('**/api/v1/dashboard/orders', (route) =>
    route.fulfill({ json: dashboardOrders }),
  )

  await page.route('**/api/v1/dashboard/orders/*/cancel', (route) =>
    route.fulfill({
      json: {
        status: 'ok',
        order: { ...dashboardOrders.orders[0], status: 'cancel_requested', cancel_requested: true },
        broker_cancel_accepted: true,
        message: 'accepted',
      },
    }),
  )

  await page.route('**/api/v1/dashboard/equity**', (route) =>
    route.fulfill({ json: dashboardEquity }),
  )

  await page.route('**/api/v1/live/runtime/sessions/*/evidence**', (route) =>
    route.fulfill({ json: liveRuntimeSessionEvidence }),
  )

  await page.route('**/api/v1/live/runtime/sessions/*/equity**', (route) =>
    route.fulfill({
      json: {
        session_id: 'live-test-001',
        points: [
          {
            timestamp: '2026-04-07T10:00:00Z',
            equity: '1000000',
            cash: '950000',
            positions_value: '50000',
          },
          {
            timestamp: '2026-04-07T11:00:00Z',
            equity: '1005000',
            cash: '950000',
            positions_value: '55000',
          },
        ],
        total: 2,
      },
    }),
  )

  await page.route('**/api/v1/live/runtime/sessions/export**', (route) =>
    route.fulfill({ body: 'session_id\nlive-test-001\n' }),
  )

  await page.route('**/api/v1/order-audit/export**', (route) =>
    route.fulfill({ body: 'record_id\naudit-001\n' }),
  )

  await page.route(/\/api\/v1\/live\/runtime\/sessions(\?.*)?$/, (route) =>
    route.fulfill({ json: liveRuntimeSessions }),
  )

  await page.route('**/api/v1/backtests/dispatcher', (route) =>
    route.fulfill({
      json: {
        running: true,
        queue_depth: 1,
        max_queue_size: 32,
        durable_queued_count: 1,
        durable_running_count: 1,
        durable_stale_count: 0,
        oldest_queued_age_seconds: 12,
      },
    }),
  )

  await page.route(/\/api\/v1\/backtests(\?.*)?$/, (route) =>
    route.fulfill({
      json: {
        runs: [backtestRunDetail],
        total: 1,
        page: 1,
        page_size: 100,
      },
    }),
  )

  await page.route('**/api/v1/backtests/retention/preview**', (route) =>
    route.fulfill({
      json: {
        cutoff: '2026-03-01T00:00:00Z',
        status: 'succeeded',
        candidate_count: 0,
        run_ids: [],
      },
    }),
  )

  await page.route('**/api/v1/backtests/*/cancel', (route) =>
    route.fulfill({ json: { ...backtestRunDetail, status: 'cancelled' } }),
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
