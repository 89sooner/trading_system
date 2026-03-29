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
    <div className="space-y-2">
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
      {status.provider && (
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          {status.provider && (
            <span>Provider: <span className="text-zinc-200">{status.provider}</span></span>
          )}
          {status.symbols && status.symbols.length > 0 && (
            <span>Symbols: <span className="text-zinc-200">{status.symbols.join(', ')}</span></span>
          )}
          {status.market_session && (
            <span>Market: <span className={cn(
              'font-medium',
              status.market_session === 'open' ? 'text-green-400' : 'text-amber-400',
            )}>{status.market_session}</span></span>
          )}
          {status.last_reconciliation_status && (
            <span>Recon: <span className={cn(
              'font-medium',
              status.last_reconciliation_status === 'completed' ? 'text-zinc-200' : 'text-amber-400',
            )}>{status.last_reconciliation_status}</span></span>
          )}
        </div>
      )}
    </div>
  )
}
