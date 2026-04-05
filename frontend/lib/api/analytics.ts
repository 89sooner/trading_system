import { requestJson } from './client'
import type { TradeAnalyticsResponse } from './types'

export const getBacktestTradeAnalytics = (runId: string) =>
  requestJson<TradeAnalyticsResponse>(`/analytics/backtests/${encodeURIComponent(runId)}/trades`)
