import { requestJson } from './client'
import type { BacktestRunRequestDTO, BacktestRunAcceptedDTO, BacktestRunStatusDTO } from './types'

export const createBacktestRun = (payload: BacktestRunRequestDTO) =>
  requestJson<BacktestRunAcceptedDTO>('/backtests', { method: 'POST', body: JSON.stringify(payload) })

export const getBacktestRun = (runId: string) =>
  requestJson<BacktestRunStatusDTO>(`/backtests/${encodeURIComponent(runId)}`)
