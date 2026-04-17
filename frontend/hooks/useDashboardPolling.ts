'use client'

import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getDashboardStatus, getDashboardPositions, getDashboardEvents } from '@/lib/api/dashboard'
import type { PositionsResponse } from '@/lib/api/types'
import type { EquityDataPoint } from '@/components/dashboard/EquityChart'

function computePortfolioValue(data: PositionsResponse): number {
  const cash = Number(data.cash)
  const positionsValue = data.positions.reduce((sum, p) => {
    const cost = Number(p.quantity) * Number(p.average_cost)
    const pnl = Number(p.unrealized_pnl ?? 0)
    return sum + cost + pnl
  }, 0)
  return cash + positionsValue
}

export function useDashboardPolling() {
  const statusQuery = useQuery({
    queryKey: ['dashboard', 'status'],
    queryFn: getDashboardStatus,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    retry: 2,
  })

  const controllerState = statusQuery.data?.controller_state
  const hasActiveRuntime = controllerState === 'active' || controllerState === 'starting'

  const positionsQuery = useQuery({
    queryKey: ['dashboard', 'positions'],
    queryFn: getDashboardPositions,
    enabled: hasActiveRuntime,
    refetchInterval: hasActiveRuntime ? 5000 : false,
    refetchIntervalInBackground: false,
    retry: 2,
  })

  const eventsQuery = useQuery({
    queryKey: ['dashboard', 'events'],
    queryFn: () => getDashboardEvents(50),
    enabled: hasActiveRuntime,
    refetchInterval: hasActiveRuntime ? 5000 : false,
    refetchIntervalInBackground: false,
    retry: 2,
  })

  const lastSuccessTime = Math.max(
    statusQuery.dataUpdatedAt,
    positionsQuery.dataUpdatedAt,
    eventsQuery.dataUpdatedAt,
  )

  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 3000)
    return () => clearInterval(id)
  }, [])

  const isLive = hasActiveRuntime && now - lastSuccessTime < 10_000 && lastSuccessTime > 0
  const equitySeries: EquityDataPoint[] =
    hasActiveRuntime && positionsQuery.data
      ? [{ time: now, value: computePortfolioValue(positionsQuery.data) }]
      : []

  return { statusQuery, positionsQuery, eventsQuery, hasActiveRuntime, isLive, equitySeries }
}
