import { StatusBadge } from '@/components/shared/StatusBadge'
import { formatUptime, formatUtcTimestamp } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import type { DashboardStatus } from '@/api/types'

interface StatusCardProps {
  status: DashboardStatus
  isLive: boolean
}

export function StatusCard({ status, isLive }: StatusCardProps) {
  return (
    <div className="flex items-center gap-6">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            isLive ? 'bg-green-400 animate-pulse' : 'bg-amber-400',
          )}
        />
        <StatusBadge state={status.state} />
      </div>
      <div className="text-xs text-zinc-400">
        Heartbeat: <span className="text-zinc-200">{formatUtcTimestamp(status.last_heartbeat)}</span>
      </div>
      <div className="text-xs text-zinc-400">
        Uptime: <span className="text-zinc-200">{formatUptime(status.uptime_seconds)}</span>
      </div>
    </div>
  )
}
