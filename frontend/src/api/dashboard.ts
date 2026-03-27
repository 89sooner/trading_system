import { requestJson } from './client'
import type { DashboardStatus, PositionsResponse, EventFeed, ControlResponse } from './types'

export const getDashboardStatus = () => requestJson<DashboardStatus>('/dashboard/status')
export const getDashboardPositions = () => requestJson<PositionsResponse>('/dashboard/positions')
export const getDashboardEvents = (limit = 50) => requestJson<EventFeed>(`/dashboard/events?limit=${limit}`)
export const postDashboardControl = (action: 'pause' | 'resume' | 'reset') =>
  requestJson<ControlResponse>('/dashboard/control', {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
