import { requestJson } from './client'
import { useApiStore } from '@/store/apiStore'
import type {
  DashboardStatus,
  PositionsResponse,
  EventFeed,
  ControlResponse,
  EquityTimeseriesResponse,
  LiveRuntimeStartRequestDTO,
  LiveRuntimeStartResponseDTO,
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
