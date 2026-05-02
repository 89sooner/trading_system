import { requestJson, requestText } from './client'
import { useApiStore } from '@/store/apiStore'
import type {
  DashboardStatus,
  PositionsResponse,
  EventFeed,
  LiveOrderCancelResponse,
  LiveOrderList,
  ControlResponse,
  EquityTimeseriesResponse,
  LivePreflightResponseDTO,
  LiveRuntimeStartRequestDTO,
  LiveRuntimeStartResponseDTO,
  LiveRuntimeSessionList,
  LiveRuntimeSessionRecord,
  LiveRuntimeSessionEvidence,
  LiveRuntimeSessionExportParams,
  LiveRuntimeSessionSearchParams,
  OrderAuditExportParams,
} from './types'

export const getDashboardStatus = () => requestJson<DashboardStatus>('/dashboard/status')
export const getDashboardPositions = () => requestJson<PositionsResponse>('/dashboard/positions')
export const getDashboardEvents = (limit = 50) => requestJson<EventFeed>(`/dashboard/events?limit=${limit}`)
export const getDashboardOrders = () => requestJson<LiveOrderList>('/dashboard/orders')
export const postDashboardOrderCancel = (recordId: string) =>
  requestJson<LiveOrderCancelResponse>(
    `/dashboard/orders/${encodeURIComponent(recordId)}/cancel`,
    { method: 'POST' },
  )
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

function sessionSearchQuery(params?: LiveRuntimeSessionSearchParams) {
  const qs = new URLSearchParams()
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.page != null) qs.set('page', String(params.page))
  if (params?.page_size != null) qs.set('page_size', String(params.page_size))
  if (params?.start) qs.set('start', params.start)
  if (params?.end) qs.set('end', params.end)
  if (params?.provider) qs.set('provider', params.provider)
  if (params?.broker) qs.set('broker', params.broker)
  if (params?.live_execution) qs.set('live_execution', params.live_execution)
  if (params?.state) qs.set('state', params.state)
  if (params?.symbol) qs.set('symbol', params.symbol)
  if (params?.has_error != null) qs.set('has_error', String(params.has_error))
  if (params?.sort) qs.set('sort', params.sort)
  return qs.toString()
}

export const listLiveRuntimeSessions = (
  params: number | LiveRuntimeSessionSearchParams = 20,
) => {
  const query = typeof params === 'number'
    ? sessionSearchQuery({ limit: params })
    : sessionSearchQuery(params)
  return requestJson<LiveRuntimeSessionList>(
    `/live/runtime/sessions${query ? `?${query}` : ''}`,
  )
}

export const getLiveRuntimeSession = (sessionId: string) =>
  requestJson<LiveRuntimeSessionRecord>(
    `/live/runtime/sessions/${encodeURIComponent(sessionId)}`,
  )

export const getLiveRuntimeSessionEquity = (sessionId: string, limit = 300) =>
  requestJson<EquityTimeseriesResponse>(
    `/live/runtime/sessions/${encodeURIComponent(sessionId)}/equity?limit=${limit}`,
  )

export const getLiveRuntimeSessionEvidence = (sessionId: string, limit = 20) =>
  requestJson<LiveRuntimeSessionEvidence>(
    `/live/runtime/sessions/${encodeURIComponent(sessionId)}/evidence?limit=${limit}`,
  )

export const exportLiveRuntimeSessions = (params: LiveRuntimeSessionExportParams = {}) => {
  const qs = new URLSearchParams(sessionSearchQuery(params))
  qs.set('format', params.format ?? 'csv')
  return requestText(`/live/runtime/sessions/export?${qs.toString()}`)
}

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
