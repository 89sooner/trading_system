'use client'

import Link from 'next/link'
import { useMemo, useState, useTransition } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock3, RefreshCw, Rows3, Trash2, Zap } from 'lucide-react'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  getBacktestDispatcherStatus,
  listBacktestRuns,
  previewBacktestRetention,
  pruneBacktestRetention,
} from '@/lib/api/backtests'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { BacktestRetentionPreview, BacktestRunListItem } from '@/lib/api/types'
import { useRunsStore, type RunRecord } from '@/store/runsStore'

const ACTIVE_STATUSES = new Set(['queued', 'running'])

function serverItemToRunRecord(item: BacktestRunListItem): RunRecord {
  return {
    runId: item.run_id,
    symbol: item.input_symbols[0] ?? '—',
    status: item.status as RunRecord['status'],
    createdAt: item.started_at,
    strategyProfile: item.metadata?.strategy_profile_id ?? null,
    metadata: item.metadata ?? undefined,
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
    key: 'route',
    header: 'Route',
    cell: (row) => (
      <span className="text-xs text-muted-foreground">
        {row.metadata?.provider ?? '-'} / {row.metadata?.broker ?? '-'}
      </span>
    ),
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
  const [retentionCutoff, setRetentionCutoff] = useState('')
  const [retentionPreview, setRetentionPreview] = useState<BacktestRetentionPreview | null>(null)
  const [retentionMessage, setRetentionMessage] = useState<string | null>(null)
  const [isRetentionPending, startRetentionTransition] = useTransition()

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

  const dispatcherQuery = useQuery({
    queryKey: ['backtests', 'dispatcher'],
    queryFn: getBacktestDispatcherStatus,
    staleTime: 5_000,
    refetchInterval: 5_000,
    retry: 1,
  })

  const rows: RunRecord[] = serverQuery.isError
    ? localRuns
    : serverQuery.data?.runs.map(serverItemToRunRecord) ?? localRuns

  const queuedCount = rows.filter((row) => row.status === 'queued').length
  const runningCount = rows.filter((row) => row.status === 'running').length
  const succeededCount = rows.filter((row) => row.status === 'succeeded').length
  const dispatcher = dispatcherQuery.data
  const defaultCutoff = useMemo(() => {
    const date = new Date()
    date.setUTCDate(date.getUTCDate() - 30)
    return date.toISOString().slice(0, 10)
  }, [])

  function previewRetention() {
    const cutoffDate = retentionCutoff || defaultCutoff
    startRetentionTransition(async () => {
      try {
        const preview = await previewBacktestRetention({
          cutoff: `${cutoffDate}T00:00:00Z`,
          status: 'succeeded',
        })
        setRetentionPreview(preview)
        setRetentionMessage(`${preview.candidate_count} completed run(s) match the cutoff.`)
      } catch {
        setRetentionMessage('Retention preview failed.')
      }
    })
  }

  function pruneRetention() {
    if (!retentionPreview) return
    startRetentionTransition(async () => {
      try {
        const result = await pruneBacktestRetention({
          cutoff: retentionPreview.cutoff,
          status: retentionPreview.status ?? undefined,
          confirm: 'DELETE',
        })
        setRetentionMessage(`${result.deleted_count} run(s) were pruned.`)
        setRetentionPreview(null)
        await serverQuery.refetch()
      } catch {
        setRetentionMessage('Retention prune failed.')
      }
    })
  }

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

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
        <SurfacePanel
          eyebrow="Dispatcher"
          title="Worker status"
          description="Current API-owned backtest dispatcher capacity and queue depth."
          action={<RefreshCw className="h-4 w-4 text-muted-foreground" />}
        >
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Worker
              </p>
              <p className="mt-2 text-sm font-medium">
                {dispatcher?.running ? 'running' : 'stopped'}
              </p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Queue depth
              </p>
              <p className="mt-2 font-mono text-2xl font-semibold">
                {dispatcher?.queue_depth ?? '-'}
              </p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Capacity
              </p>
              <p className="mt-2 font-mono text-2xl font-semibold">
                {dispatcher?.max_queue_size ?? '-'}
              </p>
            </div>
          </div>
        </SurfacePanel>

        <SurfacePanel
          eyebrow="Retention"
          title="Prune completed runs"
          description="Preview completed runs older than a UTC cutoff before deleting."
          action={<Trash2 className="h-4 w-4 text-muted-foreground" />}
        >
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="retention-cutoff">Cutoff date</Label>
              <Input
                id="retention-cutoff"
                type="date"
                value={retentionCutoff || defaultCutoff}
                onChange={(event) => {
                  setRetentionCutoff(event.target.value)
                  setRetentionPreview(null)
                  setRetentionMessage(null)
                }}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={previewRetention}
                disabled={isRetentionPending}
              >
                Preview
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={pruneRetention}
                disabled={
                  isRetentionPending ||
                  retentionPreview == null ||
                  retentionPreview.candidate_count === 0
                }
              >
                Prune
              </Button>
            </div>
            {retentionMessage ? (
              <p className="text-sm text-muted-foreground">{retentionMessage}</p>
            ) : null}
          </div>
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
