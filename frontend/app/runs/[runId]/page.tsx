'use client'

import { useQuery } from '@tanstack/react-query'
import { Download, OctagonX } from 'lucide-react'
import { use, useEffect, useTransition } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { ErrorBanner } from '@/components/domain/ErrorBanner'
import { RunDetailTabs } from '@/components/runs/RunDetailTabs'
import { Button } from '@/components/ui/button'
import { cancelBacktestRun, exportOrderAudit, getBacktestRun } from '@/lib/api/backtests'
import { getBacktestTradeAnalytics } from '@/lib/api/analytics'
import { useRunsStore } from '@/store/runsStore'

const ACTIVE_STATUSES = new Set(['queued', 'running'])

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>
}) {
  const { runId } = use(params)
  const { updateRunStatus } = useRunsStore()
  const [isCancelling, startCancelTransition] = useTransition()

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getBacktestRun(runId),
    staleTime: (query) =>
      (query.state.data as { status?: string } | undefined)?.status === 'succeeded'
        ? Infinity
        : 10_000,
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status
      return status && ACTIVE_STATUSES.has(status) ? 2_000 : false
    },
  })

  const isSucceeded = runQuery.data?.status === 'succeeded'

  const analyticsQuery = useQuery({
    queryKey: ['analytics', runId],
    queryFn: () => getBacktestTradeAnalytics(runId),
    enabled: isSucceeded,
    staleTime: isSucceeded ? Infinity : 10_000,
  })

  useEffect(() => {
    if (runQuery.data) {
      updateRunStatus(runId, runQuery.data.status)
    }
  }, [runId, runQuery.data, updateRunStatus])

  if (runQuery.isPending) {
    return <p className="text-sm text-muted-foreground">Loading run...</p>
  }
  if (runQuery.error) return <ErrorBanner error={runQuery.error} />

  const run = runQuery.data!
  const handleExportAudit = async () => {
    const body = await exportOrderAudit({
      scope: 'backtest',
      owner_id: runId,
      format: 'csv',
      limit: 5000,
    })
    const blob = new Blob([body], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${runId}-order-audit.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }
  const canCancel = ACTIVE_STATUSES.has(run.status)
  const handleCancel = () => {
    startCancelTransition(async () => {
      await cancelBacktestRun(runId)
      await runQuery.refetch()
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Run Detail"
        description={runId}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={!canCancel || isCancelling}
            >
              <OctagonX aria-hidden="true" />
              Cancel
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportAudit}>
              <Download aria-hidden="true" />
              Export audit CSV
            </Button>
            <StatusBadge state={run.status} />
          </div>
        }
      />

      {run.metadata ? (
        <SurfacePanel
          eyebrow="Run Metadata"
          title="Execution context"
          description="Server-side metadata stored with the run for later review and promotion decisions."
        >
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Route
              </p>
              <p className="mt-2 text-sm font-medium">
                {run.metadata.provider ?? '-'} / {run.metadata.broker ?? '-'}
              </p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Strategy Profile
              </p>
              <p className="mt-2 text-sm font-medium">
                {run.metadata.strategy_profile_id ?? 'inline / none'}
              </p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Source
              </p>
              <p className="mt-2 text-sm font-medium">{run.metadata.source ?? '-'}</p>
            </div>
          </div>
          {run.metadata.notes ? (
            <div className="rounded-xl border border-border/80 bg-background p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Note
              </p>
              <p className="mt-2 text-sm text-foreground">{run.metadata.notes}</p>
            </div>
          ) : null}
        </SurfacePanel>
      ) : null}

      {run.job ? (
        <SurfacePanel
          eyebrow="Worker"
          title="Execution progress"
          description="Durable worker lease, heartbeat, and cooperative cancellation state for this run."
        >
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Progress
              </p>
              <p className="mt-2 font-mono text-2xl font-semibold">
                {run.job.progress.percent.toFixed(0)}%
              </p>
              <p className="text-xs text-muted-foreground">
                {run.job.progress.processed_bars}/{run.job.progress.total_bars} bars
              </p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Worker
              </p>
              <p className="mt-2 text-sm font-medium">{run.job.worker_id ?? '-'}</p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Heartbeat
              </p>
              <p className="mt-2 text-sm font-medium">{run.job.last_heartbeat_at ?? '-'}</p>
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Attempts
              </p>
              <p className="mt-2 font-mono text-2xl font-semibold">
                {run.job.attempt_count}/{run.job.max_attempts}
              </p>
              <p className="text-xs text-muted-foreground">
                {run.job.cancel_requested ? 'cancel requested' : 'active'}
              </p>
            </div>
          </div>
        </SurfacePanel>
      ) : null}

      {run.result ? (
        <RunDetailTabs run={run} analytics={analyticsQuery.data} />
      ) : (
        <p className="text-sm text-muted-foreground">
          {run.status === 'failed'
            ? 'Run finished with failure before analytics were generated.'
            : `Run is currently ${run.status}. Waiting for terminal result...`}
        </p>
      )}

      {run.error && <ErrorBanner error={new Error(run.error)} />}
    </div>
  )
}
