import type { EventRecord } from '@/api/types'
import { cn } from '@/lib/utils'

function severityClass(sev: string): string {
  if (!sev) return 'text-zinc-400'
  if (sev.includes('WARNING')) return 'text-amber-400'
  if (sev.includes('ERROR') || sev.includes('CRITICAL')) return 'text-red-400'
  return 'text-blue-400'
}

export function EventFeed({ events }: { events: EventRecord[] }) {
  if (events.length === 0) {
    return <p className="text-xs text-zinc-500">No events yet.</p>
  }

  return (
    <div className="max-h-64 overflow-y-auto space-y-1 font-mono text-xs">
      {[...events].reverse().map((e, i) => {
        const ts = new Date(e.timestamp).toLocaleTimeString()
        const payloadStr = Object.entries(e.payload || {})
          .map(([k, v]) => `${k}=${v}`)
          .join(' ')
        return (
          <div key={i} className="flex items-start gap-2 py-0.5">
            <span className="text-zinc-500 shrink-0">{ts}</span>
            <span className={cn('shrink-0 font-semibold', severityClass(e.severity))}>
              {e.severity}
            </span>
            <span className="text-zinc-200 shrink-0 font-semibold">{e.event}</span>
            <span className="text-zinc-400 truncate">{payloadStr}</span>
          </div>
        )
      })}
    </div>
  )
}
