import { createFileRoute } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useDashboardPolling } from '@/hooks/useDashboardPolling'
import { StatusCard } from '@/components/dashboard/StatusCard'
import { ControlButtons } from '@/components/dashboard/ControlButtons'
import { PositionsTable } from '@/components/dashboard/PositionsTable'
import { EventFeed } from '@/components/dashboard/EventFeed'
import { ErrorBanner } from '@/components/shared/ErrorBanner'

export const Route = createFileRoute('/dashboard')({
  component: DashboardPage,
})

function DashboardPage() {
  const { statusQuery, positionsQuery, eventsQuery, isLive } = useDashboardPolling()

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">Live Dashboard</h1>

      <Card>
        <CardHeader><CardTitle>Runtime Status</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {statusQuery.error ? (
            <ErrorBanner error={statusQuery.error} />
          ) : statusQuery.data ? (
            <StatusCard status={statusQuery.data} isLive={isLive} />
          ) : (
            <p className="text-xs text-zinc-500">Loading...</p>
          )}
          <ControlButtons />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Positions &amp; Cash</CardTitle></CardHeader>
        <CardContent>
          {positionsQuery.error ? (
            <ErrorBanner error={positionsQuery.error} />
          ) : positionsQuery.data ? (
            <PositionsTable data={positionsQuery.data} />
          ) : (
            <p className="text-xs text-zinc-500">Loading...</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Recent Events</CardTitle></CardHeader>
        <CardContent>
          {eventsQuery.data ? (
            <EventFeed events={eventsQuery.data.events} />
          ) : (
            <p className="text-xs text-zinc-500">Loading...</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
