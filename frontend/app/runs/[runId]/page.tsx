'use client'

import { useQuery } from '@tanstack/react-query'
import { use } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusBadge } from '@/components/domain/StatusBadge'
import { StatTile } from '@/components/domain/StatTile'
import { ErrorBanner } from '@/components/domain/ErrorBanner'
import { ChartContainer } from '@/components/domain/ChartContainer'
import { RunSummaryGrid } from '@/components/runs/RunSummaryGrid'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import { DrawdownChart } from '@/components/charts/DrawdownChart'
import { TradeScatterChart } from '@/components/charts/TradeScatterChart'
import { SignalsTable } from '@/components/runs/SignalsTable'
import { FillsTable } from '@/components/runs/FillsTable'
import { TradesTable } from '@/components/runs/TradesTable'
import { getBacktestRun } from '@/lib/api/backtests'
import { getBacktestTradeAnalytics } from '@/lib/api/analytics'
import { formatPercentFromRatio, formatDecimal } from '@/lib/formatters'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>
}) {
  const { runId } = use(params)

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getBacktestRun(runId),
    staleTime: (query) =>
      (query.state.data as { status?: string } | undefined)?.status === 'succeeded'
        ? Infinity
        : 10_000,
  })

  const isSucceeded = runQuery.data?.status === 'succeeded'

  const analyticsQuery = useQuery({
    queryKey: ['analytics', runId],
    queryFn: () => getBacktestTradeAnalytics(runId),
    enabled: isSucceeded,
    staleTime: isSucceeded ? Infinity : 10_000,
  })

  if (runQuery.isPending) {
    return <p className="text-sm text-muted-foreground">Loading run...</p>
  }
  if (runQuery.error) return <ErrorBanner error={runQuery.error} />

  const run = runQuery.data!
  const result = run.result

  return (
    <div className="space-y-6">
      <PageHeader
        title="Run Detail"
        description={runId}
        actions={<StatusBadge state={run.status} />}
      />

      {result && (
        <>
          <Card>
            <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
            <CardContent>
              <RunSummaryGrid result={result} startedAt={run.started_at} finishedAt={run.finished_at} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Equity Curve</CardTitle></CardHeader>
            <CardContent>
              <ChartContainer loading={false} empty={result.equity_curve.length === 0}>
                <EquityCurveChart data={result.equity_curve} />
              </ChartContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Drawdown</CardTitle></CardHeader>
            <CardContent>
              <ChartContainer loading={false} empty={result.drawdown_curve.length === 0}>
                <DrawdownChart data={result.drawdown_curve} />
              </ChartContainer>
            </CardContent>
          </Card>

          {analyticsQuery.data && (
            <Card>
              <CardHeader><CardTitle>Trade Analytics</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  <StatTile label="Trades" value={String(analyticsQuery.data.stats.trade_count)} />
                  <StatTile label="Win Rate" value={formatPercentFromRatio(analyticsQuery.data.stats.win_rate)} />
                  <StatTile label="Risk/Reward" value={formatDecimal(analyticsQuery.data.stats.risk_reward_ratio)} />
                  <StatTile label="Max Drawdown" value={formatPercentFromRatio(analyticsQuery.data.stats.max_drawdown)} trend="down" />
                  <StatTile label="Avg Hold (s)" value={String(analyticsQuery.data.stats.average_time_in_market_seconds ?? '–')} />
                </div>
                <TradeScatterChart trades={analyticsQuery.data.trades} />
                <TradesTable trades={analyticsQuery.data.trades} />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader><CardTitle>Strategy Signals</CardTitle></CardHeader>
            <CardContent><SignalsTable signals={result.signals} /></CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Fills &amp; Rejections</CardTitle></CardHeader>
            <CardContent>
              <FillsTable events={[...(result.orders ?? []), ...(result.risk_rejections ?? [])]} />
            </CardContent>
          </Card>
        </>
      )}

      {run.error && <ErrorBanner error={new Error(run.error)} />}
    </div>
  )
}
