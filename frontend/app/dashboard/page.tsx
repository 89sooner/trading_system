'use client'

import { useDashboardStream } from '@/hooks/useDashboardStream'
import { PageHeader } from '@/components/layout/PageHeader'
import { ControlButtons } from '@/components/dashboard/ControlButtons'
import { RuntimeLaunchForm } from '@/components/dashboard/RuntimeLaunchForm'
import { DashboardMetrics } from '@/components/dashboard/DashboardMetrics'
import { PositionsPanel } from '@/components/dashboard/PositionsPanel'
import { EventTimeline } from '@/components/dashboard/EventTimeline'
import { StatusIndicator } from '@/components/domain/StatusIndicator'
import { ChartContainer } from '@/components/domain/ChartContainer'
import { EquityChart } from '@/components/dashboard/EquityChart'

export default function DashboardPage() {
  const {
    statusQuery,
    positionsQuery,
    eventsQuery,
    hasActiveRuntime,
    isLive,
    equitySeries,
    sseConnected,
  } = useDashboardStream()

  const loading = statusQuery.isLoading || (hasActiveRuntime && positionsQuery.isLoading)
  const status = statusQuery.data
  const statusLabel = hasActiveRuntime
    ? (sseConnected ? 'Connected (SSE)' : status?.state ?? 'Starting')
    : status?.controller_state === 'error'
      ? 'Controller Error'
      : 'Disconnected'

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Dashboard"
        description="Real-time trading system monitoring"
        actions={
          <div className="flex items-center gap-3">
            <StatusIndicator
              variant={sseConnected ? 'online' : hasActiveRuntime ? 'warning' : status?.last_error ? 'error' : 'offline'}
              label={statusLabel}
            />
            {hasActiveRuntime ? <ControlButtons /> : null}
          </div>
        }
      />

      {!hasActiveRuntime && <RuntimeLaunchForm />}
      {status?.last_error && !hasActiveRuntime && (
        <p className="text-sm text-danger">Last runtime error: {status.last_error}</p>
      )}

      <DashboardMetrics
        status={status}
        positions={hasActiveRuntime ? positionsQuery.data : undefined}
        isLive={isLive}
        loading={loading}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <PositionsPanel
          data={hasActiveRuntime ? positionsQuery.data : undefined}
          loading={hasActiveRuntime ? positionsQuery.isLoading : false}
        />
        <div className="space-y-2">
          <h2 className="text-sm font-medium">Equity Curve</h2>
          <ChartContainer loading={loading} empty={equitySeries.length === 0} emptyMessage="Chart available when the runtime is active.">
            <EquityChart data={equitySeries} />
          </ChartContainer>
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-medium">Event Timeline</h2>
        <EventTimeline
          events={hasActiveRuntime ? (eventsQuery.data?.events ?? []) : []}
          loading={hasActiveRuntime ? eventsQuery.isLoading : false}
        />
      </div>
    </div>
  )
}
