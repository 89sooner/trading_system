'use client'

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { getDashboardStatus, getDashboardPositions, getDashboardEvents } from '@/lib/api/dashboard'

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

  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 3000)
    return () => clearInterval(id)
  }, [])

  const isLive = now - lastSuccessTime < 10_000 && lastSuccessTime > 0

  return { statusQuery, positionsQuery, eventsQuery, isLive }
}
