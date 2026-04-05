'use client'

import { useDashboardPolling } from '@/hooks/useDashboardPolling'
import { PageHeader } from '@/components/layout/PageHeader'
import { ControlButtons } from '@/components/dashboard/ControlButtons'
import { DashboardMetrics } from '@/components/dashboard/DashboardMetrics'
import { PositionsPanel } from '@/components/dashboard/PositionsPanel'
import { EventTimeline } from '@/components/dashboard/EventTimeline'
import { StatusIndicator } from '@/components/domain/StatusIndicator'
import { ChartContainer } from '@/components/domain/ChartContainer'

export default function DashboardPage() {
  const { statusQuery, positionsQuery, eventsQuery, isLive } = useDashboardPolling()

  const loading = statusQuery.isLoading || positionsQuery.isLoading

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Dashboard"
        description="Real-time trading system monitoring"
        actions={
          <div className="flex items-center gap-3">
            <StatusIndicator
              variant={isLive ? 'online' : statusQuery.data ? 'warning' : 'offline'}
              label={isLive ? 'Connected' : 'Disconnected'}
            />
            <ControlButtons />
          </div>
        }
      />

      <DashboardMetrics
        status={statusQuery.data}
        positions={positionsQuery.data}
        isLive={isLive}
        loading={loading}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <PositionsPanel data={positionsQuery.data} loading={positionsQuery.isLoading} />
        <div className="space-y-2">
          <h2 className="text-sm font-medium">Equity Curve</h2>
          <ChartContainer loading={loading} empty={true} emptyMessage="Chart available when positions are active.">
            {null}
          </ChartContainer>
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-medium">Event Timeline</h2>
        <EventTimeline events={eventsQuery.data?.events ?? []} loading={eventsQuery.isLoading} />
      </div>
    </div>
  )
}
