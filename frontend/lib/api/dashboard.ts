import { requestJson, requestText } from './client'
import { useApiStore } from '@/store/apiStore'
import type {
  DashboardStatus,
  PositionsResponse,
  EventFeed,
  ControlResponse,
  EquityTimeseriesResponse,
  LivePreflightResponseDTO,
  LiveRuntimeStartRequestDTO,
  LiveRuntimeStartResponseDTO,
  LiveRuntimeSessionList,
  LiveRuntimeSessionRecord,
  OrderAuditExportParams,
} from './types'

export const getDashboardStatus = () => requestJson<DashboardStatus>('/dashboard/status')
export const getDashboardPositions = () => requestJson<PositionsResponse>('/dashboard/positions')
export const getDashboardEvents = (limit = 50) => requestJson<EventFeed>(`/dashboard/events?limit=${limit}`)
export const postDashboardControl = (action: 'pause' | 'resume' | 'reset' | 'stop') =>
  requestJson<ControlResponse>('/dashboard/control', {
    method: 'POST',
    body: JSON.stringify({ action }),
  })

export const getDashboardEquity = (limit = 300) =>
  requestJson<EquityTimeseriesResponse>(`/dashboard/equity?limit=${limit}`)

export const postLivePreflight = (payload: LiveRuntimeStartRequestDTO) =>
  requestJson<LivePreflightResponseDTO>('/live/preflight', {
    method: 'POST',
    body: JSON.stringify({ mode: 'live', ...payload }),
  })

/** Build the SSE stream URL including the optional api_key query param. */
export function getDashboardStreamUrl(): string {
  const { baseUrl, apiKey } = useApiStore.getState()
  const url = `${baseUrl}/dashboard/stream`
  if (apiKey) return `${url}?api_key=${encodeURIComponent(apiKey)}`
  return url
}


export const postLiveRuntimeStart = (payload: LiveRuntimeStartRequestDTO) =>
  requestJson<LiveRuntimeStartResponseDTO>('/live/runtime/start', {
    method: 'POST',
    body: JSON.stringify({ mode: 'live', ...payload }),
  })

export const listLiveRuntimeSessions = (limit = 20) =>
  requestJson<LiveRuntimeSessionList>(`/live/runtime/sessions?limit=${limit}`)

export const getLiveRuntimeSession = (sessionId: string) =>
  requestJson<LiveRuntimeSessionRecord>(
    `/live/runtime/sessions/${encodeURIComponent(sessionId)}`,
  )

export const exportLiveSessionOrderAudit = (params: Omit<OrderAuditExportParams, 'scope'>) => {
  const qs = new URLSearchParams()
  qs.set('scope', 'live_session')
  qs.set('owner_id', params.owner_id)
  qs.set('format', params.format ?? 'csv')
  if (params.start) qs.set('start', params.start)
  if (params.end) qs.set('end', params.end)
  if (params.status) qs.set('status', params.status)
  if (params.side) qs.set('side', params.side)
  if (params.broker_order_id) qs.set('broker_order_id', params.broker_order_id)
  if (params.limit != null) qs.set('limit', String(params.limit))
  return requestText(`/order-audit/export?${qs.toString()}`)
}
