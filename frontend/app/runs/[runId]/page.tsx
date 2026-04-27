'use client'

import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { use, useEffect } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { ErrorBanner } from '@/components/domain/ErrorBanner'
import { RunDetailTabs } from '@/components/runs/RunDetailTabs'
import { Button } from '@/components/ui/button'
import { exportOrderAudit, getBacktestRun } from '@/lib/api/backtests'
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Run Detail"
        description={runId}
        actions={
          <div className="flex items-center gap-2">
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
