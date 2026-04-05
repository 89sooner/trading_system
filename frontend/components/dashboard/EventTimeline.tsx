'use client'

import type { EventRecord } from '@/lib/api/types'
import { cn } from '@/lib/utils'

function severityColor(sev: string): string {
  if (sev.includes('WARNING') || sev === '30') return 'text-warning'
  if (sev.includes('ERROR') || sev.includes('CRITICAL') || sev === '40' || sev === '50') return 'text-danger'
  return 'text-info'
}

function eventColor(event: string): string {
  if (event.startsWith('portfolio.reconciliation.')) return 'text-warning'
  if (event.startsWith('risk.')) return 'text-danger'
  return 'text-foreground'
}

interface EventTimelineProps {
  events: EventRecord[]
  loading?: boolean
}

export function EventTimeline({ events, loading }: EventTimelineProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-2">
            <div className="h-3 w-16 animate-pulse rounded bg-muted" />
            <div className="h-3 w-12 animate-pulse rounded bg-muted" />
            <div className="h-3 w-32 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
    )
  }

  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No events yet.</p>
  }

  return (
    <div className="max-h-72 overflow-y-auto space-y-0.5 font-mono text-xs">
      {[...events].reverse().map((e, i) => {
        const ts = new Date(e.timestamp).toLocaleTimeString()
        const payloadStr = Object.entries(e.payload || {})
          .map(([k, v]) => `${k}=${v}`)
          .join(' ')
        return (
          <div key={i} className="flex items-start gap-2 py-0.5">
            <span className="text-muted-foreground shrink-0">{ts}</span>
            <span className={cn('shrink-0 font-semibold', severityColor(e.severity))}>
              {e.severity}
            </span>
            <span className={cn('shrink-0 font-semibold', eventColor(e.event))}>{e.event}</span>
            <span className="text-muted-foreground truncate">{payloadStr}</span>
          </div>
        )
      })}
    </div>
  )
}
