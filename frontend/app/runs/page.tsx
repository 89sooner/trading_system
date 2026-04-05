'use client'

import { useQueries } from '@tanstack/react-query'
import Link from 'next/link'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { Button } from '@/components/ui/button'
import { useRunsStore, type RunRecord } from '@/store/runsStore'
import { getBacktestRun } from '@/lib/api/backtests'
import { formatUtcTimestamp } from '@/lib/formatters'
import { RefreshCw } from 'lucide-react'

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
  const { runs, updateRunStatus } = useRunsStore()

  const queries = useQueries({
    queries: runs.map((run) => ({
      queryKey: ['run', run.runId],
      queryFn: () => getBacktestRun(run.runId),
      staleTime: run.status === 'succeeded' || run.status === 'failed' ? Infinity : 0,
      enabled: run.status !== 'succeeded' && run.status !== 'failed',
    })),
  })

  function handleRefresh() {
    queries.forEach((q, i) => {
      q.refetch().then((res) => {
        if (res.data) updateRunStatus(runs[i].runId, res.data.status)
      })
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtest Runs"
        description="View and manage backtest execution history"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="mr-1 h-3 w-3" /> Refresh
          </Button>
        }
      />
      <DataTable
        columns={columns}
        data={runs}
        keyExtractor={(row) => row.runId}
        emptyMessage="No runs yet."
      />
    </div>
  )
}
