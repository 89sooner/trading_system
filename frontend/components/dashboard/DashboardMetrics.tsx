'use client'

import { MetricCard } from '@/components/domain/MetricCard'
import { StatusIndicator } from '@/components/domain/StatusIndicator'
import type { DashboardStatus, PositionsResponse } from '@/lib/api/types'
import { formatCurrency, formatUptime } from '@/lib/formatters'

interface DashboardMetricsProps {
  status: DashboardStatus | undefined
  positions: PositionsResponse | undefined
  isLive: boolean
  loading: boolean
}

export function DashboardMetrics({ status, positions, isLive, loading }: DashboardMetricsProps) {
  const positionCount = positions?.positions.length ?? 0
  const totalUnrealized = positions?.positions.reduce((sum, p) => {
    const pnl = Number(p.unrealized_pnl)
    return sum + (Number.isFinite(pnl) ? pnl : 0)
  }, 0) ?? 0

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label="Cash"
        value={loading ? '-' : formatCurrency(positions?.cash)}
        loading={loading}
      />
      <MetricCard
        label="Unrealized P&L"
        value={loading ? '-' : formatCurrency(totalUnrealized)}
        trend={totalUnrealized > 0 ? 'up' : totalUnrealized < 0 ? 'down' : 'neutral'}
        loading={loading}
      />
      <MetricCard
        label="Open Positions"
        value={loading ? '-' : positionCount}
        loading={loading}
      />
      <div className="flex flex-col gap-2 rounded-xl border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">System Status</p>
        <div className="flex items-center gap-2">
          <StatusIndicator
            variant={isLive ? 'online' : status ? 'warning' : 'offline'}
            label={isLive ? 'Live' : status?.state ?? 'Disconnected'}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Uptime: <span className="font-mono text-foreground">{formatUptime(status?.uptime_seconds)}</span>
        </p>
        {status?.market_session && (
          <p className="text-xs text-muted-foreground">
            Market:{' '}
            <span className={status.market_session === 'open' ? 'text-success' : 'text-warning'}>
              {status.market_session}
            </span>
          </p>
        )}
      </div>
    </div>
  )
}
