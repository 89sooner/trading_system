'use client'

import { Badge } from '@/components/ui/badge'
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
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border/80 bg-muted/20 p-4">
            <div className="flex gap-2">
              <div className="h-3 w-16 animate-pulse rounded bg-muted" />
              <div className="h-3 w-12 animate-pulse rounded bg-muted" />
            </div>
            <div className="mt-3 h-3 w-40 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-border/80 bg-muted/20 px-6 py-10 text-center">
        <p className="text-sm text-muted-foreground">No events yet.</p>
      </div>
    )
  }

  return (
    <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
      {[...events].reverse().map((e, i) => {
        const ts = new Date(e.timestamp).toLocaleTimeString()
        const payloadStr = Object.entries(e.payload || {})
          .map(([k, v]) => `${k}=${v}`)
          .join(' ')
        return (
          <div
            key={i}
            className="rounded-xl border border-border/80 bg-background px-4 py-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="shrink-0 text-xs text-muted-foreground">{ts}</span>
              <Badge variant="outline" className={cn('font-semibold', severityColor(e.severity))}>
                {e.severity}
              </Badge>
              <span className={cn('text-sm font-medium', eventColor(e.event))}>{e.event}</span>
            </div>
            <p className="mt-2 truncate font-mono text-xs text-muted-foreground">
              {payloadStr || 'No payload'}
            </p>
          </div>
        )
      })}
    </div>
  )
}
