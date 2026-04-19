'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Clock3, RefreshCw, Rows3, Zap } from 'lucide-react'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { listBacktestRuns } from '@/lib/api/backtests'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { BacktestRunListItem } from '@/lib/api/types'
import { useRunsStore, type RunRecord } from '@/store/runsStore'

const ACTIVE_STATUSES = new Set(['queued', 'running'])

function serverItemToRunRecord(item: BacktestRunListItem): RunRecord {
  return {
    runId: item.run_id,
    symbol: item.input_symbols[0] ?? '—',
    status: item.status as RunRecord['status'],
    createdAt: item.started_at,
    strategyProfile: null,
  }
}

const columns: Column<RunRecord>[] = [
  {
    key: 'runId',
    header: 'Run ID',
    cell: (row) => <span className="font-mono text-xs">{row.runId.slice(0, 8)}…</span>,
  },
  {
    key: 'symbol',
    header: 'Symbol',
    cell: (row) => <span className="font-mono">{row.symbol}</span>,
  },
  {
    key: 'status',
    header: 'Status',
    cell: (row) => <StatusBadge state={row.status} />,
  },
  {
    key: 'createdAt',
    header: 'Created',
    cell: (row) => <span className="text-xs">{formatUtcTimestamp(row.createdAt)}</span>,
  },
  {
    key: 'actions',
    header: '',
    cell: (row) => (
      <Link href={`/runs/${row.runId}`} className="text-xs text-info hover:underline">
        View
      </Link>
    ),
  },
]

export default function RunsPage() {
  const { runs: localRuns } = useRunsStore()

  const serverQuery = useQuery({
    queryKey: ['backtests', 'list'],
    queryFn: () => listBacktestRuns({ page_size: 100 }),
    staleTime: 30_000,
    retry: 1,
    refetchInterval: (query) => {
      const data = query.state.data
      const hasActiveRun = data?.runs.some((run) => ACTIVE_STATUSES.has(run.status)) ?? false
      return hasActiveRun ? 2_000 : false
    },
  })

  const rows: RunRecord[] = serverQuery.isError
    ? localRuns
    : serverQuery.data?.runs.map(serverItemToRunRecord) ?? localRuns

  const queuedCount = rows.filter((row) => row.status === 'queued').length
  const runningCount = rows.filter((row) => row.status === 'running').length
  const succeededCount = rows.filter((row) => row.status === 'succeeded').length

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtest Runs"
        description="Track queued, running, and completed backtests from the shared server-side run history."
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Server-first history</Badge>
            <Badge variant="outline">Auto-refresh on active runs</Badge>
            <Badge variant="outline">Run detail deep-links</Badge>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <SurfacePanel
          eyebrow="Queue"
          title="Queued"
          description="Runs accepted by the API and waiting for execution."
          action={<Clock3 className="h-4 w-4 text-muted-foreground" />}
        >
          <p className="font-mono text-3xl font-semibold">{queuedCount}</p>
        </SurfacePanel>
        <SurfacePanel
          eyebrow="Execution"
          title="Running"
          description="Runs currently being processed by the backtest dispatcher."
          action={<Zap className="h-4 w-4 text-muted-foreground" />}
        >
          <p className="font-mono text-3xl font-semibold">{runningCount}</p>
        </SurfacePanel>
        <SurfacePanel
          eyebrow="History"
          title="Completed"
          description="Runs already available for detail review and analytics."
          action={<Rows3 className="h-4 w-4 text-muted-foreground" />}
        >
          <p className="font-mono text-3xl font-semibold">{succeededCount}</p>
        </SurfacePanel>
      </div>

      <SurfacePanel
        eyebrow="Run History"
        title="All runs"
        description="The API is the primary source of truth. Local storage is used only as a fallback when the backend is unavailable."
        action={
          <Button variant="outline" size="sm" onClick={() => serverQuery.refetch()}>
            <RefreshCw className="mr-1 h-3 w-3" /> Refresh
          </Button>
        }
      >
        <DataTable
          columns={columns}
          data={rows}
          keyExtractor={(row) => row.runId}
          emptyMessage="No runs yet."
        />
      </SurfacePanel>
    </div>
  )
}
