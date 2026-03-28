import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getBacktestRun } from '@/api/backtests'
import { getBacktestTradeAnalytics } from '@/api/analytics'
import { RunSummaryGrid } from '@/components/runs/RunSummaryGrid'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import { DrawdownChart } from '@/components/charts/DrawdownChart'
import { TradeScatterChart } from '@/components/charts/TradeScatterChart'
import { SignalsTable } from '@/components/runs/SignalsTable'
import { FillsTable } from '@/components/runs/FillsTable'
import { TradesTable } from '@/components/runs/TradesTable'
import { StatTile } from '@/components/shared/StatTile'
import { ErrorBanner } from '@/components/shared/ErrorBanner'
import { formatPercentFromRatio, formatDecimal } from '@/lib/formatters'

export const Route = createFileRoute('/runs/$runId')({
  component: RunDetailPage,
})

function RunDetailPage() {
  const { runId } = Route.useParams()

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

  if (runQuery.isPending) return <p className="text-sm text-zinc-400">Loading run...</p>
  if (runQuery.error) return <ErrorBanner error={runQuery.error} />

  const run = runQuery.data!
  const result = run.result

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-zinc-100">Run</h1>
        <span className="font-mono text-xs text-zinc-400">{runId}</span>
        <span className={`text-xs font-semibold ${
          isSucceeded ? 'text-green-400' :
          run.status === 'failed' ? 'text-red-400' : 'text-amber-400'
        }`}>
          {run.status}
        </span>
      </div>

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
            <CardContent><EquityCurveChart data={result.equity_curve} /></CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Drawdown</CardTitle></CardHeader>
            <CardContent><DrawdownChart data={result.drawdown_curve} /></CardContent>
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
