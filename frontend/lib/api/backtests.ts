import { requestJson } from './client'
import type {
  BacktestRunRequestDTO,
  BacktestRunAcceptedDTO,
  BacktestRunStatusDTO,
  BacktestRunListResponse,
} from './types'

export const createBacktestRun = (payload: BacktestRunRequestDTO) =>
  requestJson<BacktestRunAcceptedDTO>('/backtests', { method: 'POST', body: JSON.stringify(payload) })

export const getBacktestRun = (runId: string) =>
  requestJson<BacktestRunStatusDTO>(`/backtests/${encodeURIComponent(runId)}`)

export const listBacktestRuns = (params?: {
  page?: number
  page_size?: number
  status?: string
  mode?: string
}) => {
  const qs = new URLSearchParams()
  if (params?.page != null) qs.set('page', String(params.page))
  if (params?.page_size != null) qs.set('page_size', String(params.page_size))
  if (params?.status) qs.set('status', params.status)
  if (params?.mode) qs.set('mode', params.mode)
  const query = qs.toString()
  return requestJson<BacktestRunListResponse>(`/backtests${query ? `?${query}` : ''}`)
}
