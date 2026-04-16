'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { Button } from '@/components/ui/button'
import { useRunsStore, type RunRecord } from '@/store/runsStore'
import { listBacktestRuns } from '@/lib/api/backtests'
import { formatUtcTimestamp } from '@/lib/formatters'
import { RefreshCw } from 'lucide-react'
import type { BacktestRunListItem } from '@/lib/api/types'

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

  // Server API is the primary source; fall back to localStorage on error.
  const rows: RunRecord[] = serverQuery.isError
    ? localRuns
    : (serverQuery.data?.runs.map(serverItemToRunRecord) ?? localRuns)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtest Runs"
        description="View and manage backtest execution history"
        actions={
          <Button variant="outline" size="sm" onClick={() => serverQuery.refetch()}>
            <RefreshCw className="mr-1 h-3 w-3" /> Refresh
          </Button>
        }
      />
      <DataTable
        columns={columns}
        data={rows}
        keyExtractor={(row) => row.runId}
        emptyMessage="No runs yet."
      />
    </div>
  )
}
