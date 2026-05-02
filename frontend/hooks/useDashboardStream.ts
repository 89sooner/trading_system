'use client'

import { useEffect, useRef, useState } from 'react'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { useDashboardPolling } from '@/hooks/useDashboardPolling'
import { getDashboardStreamUrl, getDashboardEquity } from '@/lib/api/dashboard'
import type { EquityDataPoint } from '@/components/dashboard/EquityChart'

export function useDashboardStream() {
  const queryClient = useQueryClient()
  const polling = useDashboardPolling()
  const [sseConnectedState, setSseConnectedState] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  const equityHistoryQuery = useQuery({
    queryKey: ['dashboard', 'equity'],
    queryFn: () => getDashboardEquity(300),
    staleTime: Infinity,
    retry: 1,
    enabled: polling.hasActiveRuntime,
  })

  const [liveEquityPoints, setLiveEquityPoints] = useState<EquityDataPoint[]>([])

  const serverEquitySeries: EquityDataPoint[] =
    equityHistoryQuery.data?.points.map((p) => ({
      time: new Date(p.timestamp).getTime(),
      value: parseFloat(p.equity),
    })) ?? []

  const equitySeries: EquityDataPoint[] = (() => {
    if (!polling.hasActiveRuntime) return []
    if (liveEquityPoints.length === 0) {
      return serverEquitySeries.length > 0 ? serverEquitySeries : polling.equitySeries
    }
    const merged = [...serverEquitySeries, ...liveEquityPoints]
    const seen = new Set<number>()
    return merged.filter((p) => {
      if (seen.has(p.time)) return false
      seen.add(p.time)
      return true
    }).slice(-300)
  })()

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (!polling.hasActiveRuntime) {
      esRef.current?.close()
      esRef.current = null
      return
    }

    const url = getDashboardStreamUrl()
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      setSseConnectedState(true)
      setLiveEquityPoints([])
    }

    es.addEventListener('status', (e) => {
      try {
        const msg = JSON.parse(e.data)
        queryClient.setQueryData(['dashboard', 'status'], (old: unknown) =>
          old ? { ...(old as object), ...msg.payload } : msg.payload
        )
      } catch {}
    })

    es.addEventListener('position', () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'positions'] })
    })

    es.addEventListener('event', () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'events'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'orders'] })
    })

    es.addEventListener('equity', (e) => {
      try {
        const msg = JSON.parse(e.data)
        const payload = msg.payload as { equity?: string; timestamp?: string }
        if (payload.equity && payload.timestamp) {
          const point: EquityDataPoint = {
            time: new Date(payload.timestamp).getTime(),
            value: parseFloat(payload.equity),
          }
          setLiveEquityPoints((prev) => [...prev.slice(-299), point])
        }
      } catch {}
    })

    es.onerror = () => {
      setSseConnectedState(false)
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
      setSseConnectedState(false)
    }
  }, [polling.hasActiveRuntime, queryClient])

  return {
    ...polling,
    equitySeries,
    sseConnected: polling.hasActiveRuntime && sseConnectedState,
  }
}
