import { requestJson } from './client'
import type {
  BacktestRunRequestDTO,
  BacktestRunAcceptedDTO,
  BacktestRunStatusDTO,
  BacktestRunListResponse,
  BacktestDispatcherStatus,
  BacktestRetentionPreview,
  BacktestRetentionPruneResponse,
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

export const getBacktestDispatcherStatus = () =>
  requestJson<BacktestDispatcherStatus>('/backtests/dispatcher')

export const previewBacktestRetention = (params: { cutoff: string; status?: string }) => {
  const qs = new URLSearchParams()
  qs.set('cutoff', params.cutoff)
  if (params.status) qs.set('status', params.status)
  return requestJson<BacktestRetentionPreview>(`/backtests/retention/preview?${qs.toString()}`)
}

export const pruneBacktestRetention = (payload: {
  cutoff: string
  status?: string
  confirm: 'DELETE'
}) =>
  requestJson<BacktestRetentionPruneResponse>('/backtests/retention/prune', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
