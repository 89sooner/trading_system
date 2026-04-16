'use client'

import { useQuery } from '@tanstack/react-query'
import { use, useEffect } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { ErrorBanner } from '@/components/domain/ErrorBanner'
import { RunDetailTabs } from '@/components/runs/RunDetailTabs'
import { getBacktestRun } from '@/lib/api/backtests'
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Run Detail"
        description={runId}
        actions={<StatusBadge state={run.status} />}
      />

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
