export type BacktestRunStatus = 'queued' | 'running' | 'succeeded' | 'failed'

// Dashboard
export interface DashboardStatus {
  state: string
  last_heartbeat: string | null
  uptime_seconds: number | null
  controller_state?: string | null
  session_id?: string | null
  live_execution?: string | null
  last_error?: string | null
  provider?: string | null
  symbols?: string[] | null
  market_session?: string | null
  last_reconciliation_at?: string | null
  last_reconciliation_status?: string | null
}

export interface Position {
  symbol: string
  quantity: string
  average_cost: string
  unrealized_pnl: string | null
}

export interface PositionsResponse {
  positions: Position[]
  cash: string
}

export interface EventRecord {
  event: string
  severity: string
  correlation_id: string
  timestamp: string
  payload: Record<string, unknown>
}

export interface EventFeed {
  events: EventRecord[]
  total: number
}

export interface ControlResponse {
  status: string
  state: string
}

export interface LiveRuntimeStartRequestDTO {
  mode?: 'live'
  symbols: string[]
  provider?: 'mock' | 'csv' | 'kis'
  broker?: 'paper' | 'kis'
  live_execution?: 'paper' | 'live'
}

export interface LiveRuntimeStartResponseDTO {
  status: 'started'
  session_id: string
  state: string
  started_at: string
  symbols: string[]
  provider: string
  broker: string
  live_execution: 'paper' | 'live'
}

// Backtests
export interface RiskDTO {
  max_position: number
  max_notional: number
  max_order_size: number
}

export interface PortfolioRiskDTO {
  max_daily_drawdown_pct?: number | null
  sl_pct?: number | null
  tp_pct?: number | null
}

export interface BacktestConfigDTO {
  starting_cash?: number
  fee_bps?: number
  trade_quantity?: number
}

export interface StrategyConfigDTO {
  type: string
  profile_id?: string | null
  pattern_set_id?: string
  label_to_side?: Record<string, string>
  trade_quantity?: number | null
  threshold_overrides?: Record<string, number>
}

export interface BacktestRunRequestDTO {
  mode: string
  symbols: string[]
  provider?: string
  broker?: string
  risk?: RiskDTO
  portfolio_risk?: PortfolioRiskDTO
  backtest?: BacktestConfigDTO
  strategy: StrategyConfigDTO
}

export interface BacktestRunAcceptedDTO {
  run_id: string
  status: BacktestRunStatus
}

export interface EquityPoint {
  timestamp: string
  equity: string
}

export interface DrawdownPoint {
  timestamp: string
  drawdown: string
}

export interface BacktestResult {
  summary: {
    return: string
    max_drawdown: string
    volatility: string
    win_rate: string
  }
  equity_curve: EquityPoint[]
  drawdown_curve: DrawdownPoint[]
  signals: EventRecord[]
  orders: EventRecord[]
  risk_rejections: EventRecord[]
}

export interface BacktestRunStatusDTO {
  run_id: string
  status: BacktestRunStatus
  started_at: string
  finished_at: string | null
  input_symbols: string[]
  mode: string
  result?: BacktestResult | null
  error?: string | null
}

// Backtest run list (Phase 8)
export interface BacktestRunListItem {
  run_id: string
  status: BacktestRunStatus
  started_at: string
  finished_at: string | null
  input_symbols: string[]
  mode: string
}

export interface BacktestRunListResponse {
  runs: BacktestRunListItem[]
  total: number
  page: number
  page_size: number
}

// Equity timeseries (Phase 8)
export interface EquityTimeseriesPoint {
  timestamp: string
  equity: string
  cash: string
  positions_value: string
}

export interface EquityTimeseriesResponse {
  session_id: string
  points: EquityTimeseriesPoint[]
  total: number
}

// Analytics
export interface TradeStats {
  trade_count: number
  win_rate: string
  risk_reward_ratio: string
  max_drawdown: string
  average_time_in_market_seconds: number | null
}

export interface Trade {
  symbol: string
  entry_time: string
  exit_time: string
  entry_price: string
  exit_price: string
  quantity: string
  pnl: string
  holding_seconds: number
}

export interface TradeAnalyticsResponse {
  stats: TradeStats
  trades: Trade[]
}

// Patterns
export interface PatternDTO {
  label: string
  lookback: number
  sample_size: number
  threshold: number
  prototype: number[]
}

export interface PatternSetDTO {
  pattern_set_id: string
  name: string
  symbol: string
  default_threshold: number
  examples_count: number
  patterns: PatternDTO[]
}

// Admin
export interface ApiKeyListItem {
  key_id: string
  name: string
  key_preview: string
  created_at: string
}

export interface CreateApiKeyResponse {
  key_id: string
  name: string
  key: string
  created_at: string
}

// Strategies
export interface StrategyProfileDTO {
  strategy_id: string
  name: string
  strategy: StrategyConfigDTO
}
