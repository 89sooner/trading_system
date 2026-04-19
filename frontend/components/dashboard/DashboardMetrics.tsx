'use client'

import { Card, CardContent } from '@/components/ui/card'
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
  const systemLabel = isLive
    ? 'Live'
    : status?.controller_state === 'starting'
      ? 'Starting'
      : status?.controller_state === 'error'
        ? 'Error'
        : status?.state ?? 'Disconnected'
  const runtimeSummary = [status?.provider, status?.broker, status?.live_execution]
    .filter(Boolean)
    .join(' / ')

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
      <Card>
        <CardContent className="flex flex-col gap-2 p-4">
          <p className="text-xs font-medium text-muted-foreground">System Status</p>
          <div className="flex items-center gap-2">
            <StatusIndicator
              variant={isLive ? 'online' : status ? 'warning' : 'offline'}
              label={systemLabel}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Uptime:{' '}
            <span className="font-mono text-foreground">{formatUptime(status?.uptime_seconds)}</span>
          </p>
          {runtimeSummary ? (
            <p className="text-xs text-muted-foreground">
              Route: <span className="font-mono text-foreground">{runtimeSummary}</span>
            </p>
          ) : null}
          {status?.market_session ? (
            <p className="text-xs text-muted-foreground">
              Market:{' '}
              <span className={status.market_session === 'open' ? 'text-success' : 'text-warning'}>
                {status.market_session}
              </span>
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
