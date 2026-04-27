'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { History, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { DashboardPanel } from '@/components/dashboard/DashboardPanel'
import { SessionDetailDialog } from '@/components/dashboard/SessionDetailDialog'
import { listLiveRuntimeSessions } from '@/lib/api/dashboard'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { LiveRuntimeSessionRecord } from '@/lib/api/types'

const columns: Column<LiveRuntimeSessionRecord>[] = [
  {
    key: 'session',
    header: 'Session',
    cell: (row) => <span className="font-mono text-xs">{row.session_id}</span>,
  },
  {
    key: 'route',
    header: 'Route',
    cell: (row) => (
      <span className="text-xs text-muted-foreground">
        {row.provider} / {row.broker} / {row.live_execution}
      </span>
    ),
  },
  {
    key: 'state',
    header: 'State',
    cell: (row) => (
      <Badge variant={row.last_state === 'error' ? 'destructive' : 'outline'}>
        {row.last_state}
      </Badge>
    ),
  },
  {
    key: 'started',
    header: 'Started',
    cell: (row) => <span className="text-xs">{formatUtcTimestamp(row.started_at)}</span>,
  },
]

export function SessionHistoryPanel() {
  const [selected, setSelected] = useState<LiveRuntimeSessionRecord | null>(null)
  const sessionsQuery = useQuery({
    queryKey: ['live-runtime', 'sessions'],
    queryFn: () => listLiveRuntimeSessions(10),
    staleTime: 15_000,
    retry: 1,
  })

  const sessions = sessionsQuery.data?.sessions ?? []

  return (
    <>
      <DashboardPanel
        eyebrow="Session history"
        title="Recent sessions"
        description="Durable live runtime sessions recorded by the API process."
        action={
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            <Button variant="outline" size="sm" onClick={() => sessionsQuery.refetch()}>
              <RefreshCw className="mr-1 h-3 w-3" />
              Refresh
            </Button>
          </div>
        }
      >
        {sessionsQuery.isError ? (
          <div className="rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm">
            Session history could not be loaded.
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={sessions}
            keyExtractor={(row) => row.session_id}
            loading={sessionsQuery.isLoading}
            loadingRows={3}
            emptyMessage="No live runtime sessions have been recorded yet."
            onRowClick={(row) => setSelected(row)}
          />
        )}
      </DashboardPanel>

      <SessionDetailDialog
        session={selected}
        open={selected != null}
        onOpenChange={(open) => {
          if (!open) setSelected(null)
        }}
      />
    </>
  )
}
