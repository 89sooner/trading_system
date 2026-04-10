'use client'

import { useEffect, useRef, useState } from 'react'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { useDashboardPolling } from '@/hooks/useDashboardPolling'
import { getDashboardStreamUrl, getDashboardEquity } from '@/lib/api/dashboard'
import type { EquityDataPoint } from '@/components/dashboard/EquityChart'

const SSE_REFETCH_INTERVAL = 0       // polling disabled while SSE is active
const POLL_REFETCH_INTERVAL = 5_000  // fallback poll interval

/**
 * Extends useDashboardPolling with an SSE connection.
 * - On successful SSE connection: disables polling refetch.
 * - On SSE status/position/event: pushes updates into the react-query cache.
 * - On SSE equity: appends to the equity series.
 * - On SSE error or close: restores polling fallback.
 */
export function useDashboardStream() {
  const queryClient = useQueryClient()
  const polling = useDashboardPolling()
  const [sseConnected, setSseConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  // Server-side equity history (loaded once on mount)
  const equityHistoryQuery = useQuery({
    queryKey: ['dashboard', 'equity'],
    queryFn: () => getDashboardEquity(300),
    staleTime: Infinity,
    retry: 1,
  })

  // Build equity series: start with server history, then live SSE points
  const [liveEquityPoints, setLiveEquityPoints] = useState<EquityDataPoint[]>([])

  const serverEquitySeries: EquityDataPoint[] =
    equityHistoryQuery.data?.points.map((p) => ({
      time: new Date(p.timestamp).getTime(),
      value: parseFloat(p.equity),
    })) ?? []

  // Merge server history + live SSE points (dedup by time)
  const equitySeries: EquityDataPoint[] = (() => {
    if (liveEquityPoints.length === 0) {
      // Fall back to polling-accumulated series while no SSE equity received
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

    const url = getDashboardStreamUrl()
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      setSseConnected(true)
      // Disable polling while SSE is live
      queryClient.setQueryDefaults(['dashboard', 'status'], { refetchInterval: SSE_REFETCH_INTERVAL })
      queryClient.setQueryDefaults(['dashboard', 'positions'], { refetchInterval: SSE_REFETCH_INTERVAL })
      queryClient.setQueryDefaults(['dashboard', 'events'], { refetchInterval: SSE_REFETCH_INTERVAL })
    }

    es.addEventListener('status', (e) => {
      try {
        const msg = JSON.parse(e.data)
        queryClient.setQueryData(['dashboard', 'status'], (old: unknown) =>
          old ? { ...(old as object), ...msg.payload } : msg.payload
        )
      } catch { /* ignore malformed */ }
    })

    es.addEventListener('position', (e) => {
      try {
        const msg = JSON.parse(e.data)
        // Invalidate positions so next manual refetch gets fresh data
        void queryClient.invalidateQueries({ queryKey: ['dashboard', 'positions'] })
        void msg // suppress unused warning
      } catch { /* ignore */ }
    })

    es.addEventListener('event', (e) => {
      try {
        // Append to events feed by invalidating — next refetch picks it up
        void queryClient.invalidateQueries({ queryKey: ['dashboard', 'events'] })
        void e
      } catch { /* ignore */ }
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
      } catch { /* ignore */ }
    })

    es.onerror = () => {
      // Restore polling fallback
      setSseConnected(false)
      queryClient.setQueryDefaults(['dashboard', 'status'], { refetchInterval: POLL_REFETCH_INTERVAL })
      queryClient.setQueryDefaults(['dashboard', 'positions'], { refetchInterval: POLL_REFETCH_INTERVAL })
      queryClient.setQueryDefaults(['dashboard', 'events'], { refetchInterval: POLL_REFETCH_INTERVAL })
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
      setSseConnected(false)
      // Restore polling on unmount
      queryClient.setQueryDefaults(['dashboard', 'status'], { refetchInterval: POLL_REFETCH_INTERVAL })
      queryClient.setQueryDefaults(['dashboard', 'positions'], { refetchInterval: POLL_REFETCH_INTERVAL })
      queryClient.setQueryDefaults(['dashboard', 'events'], { refetchInterval: POLL_REFETCH_INTERVAL })
    }
  }, [queryClient])

  return {
    ...polling,
    equitySeries,
    sseConnected,
  }
}
