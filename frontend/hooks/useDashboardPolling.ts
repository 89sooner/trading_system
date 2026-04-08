'use client'

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useRef, useMemo } from 'react'
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

  const positionsQuery = useQuery({
    queryKey: ['dashboard', 'positions'],
    queryFn: getDashboardPositions,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    retry: 2,
  })

  const eventsQuery = useQuery({
    queryKey: ['dashboard', 'events'],
    queryFn: () => getDashboardEvents(50),
    refetchInterval: 5000,
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

  const isLive = now - lastSuccessTime < 10_000 && lastSuccessTime > 0

  // Accumulate equity time series from polling responses.
  // Uses a ref for mutable accumulation and useMemo to snapshot on each data update.
  const equityRef = useRef<{ series: EquityDataPoint[]; lastTs: number }>({ series: [], lastTs: 0 })

  const equitySeries = useMemo(() => {
    const data = positionsQuery.data
    if (!data) return equityRef.current.series
    const ts = Date.now()
    // Throttle: record at most once per 5s to avoid duplicates
    if (ts - equityRef.current.lastTs < 5000) return equityRef.current.series
    equityRef.current.lastTs = ts
    const value = computePortfolioValue(data)
    equityRef.current.series = [...equityRef.current.series.slice(-299), { time: ts, value }]
    return equityRef.current.series
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positionsQuery.dataUpdatedAt])

  return { statusQuery, positionsQuery, eventsQuery, isLive, equitySeries }
}
