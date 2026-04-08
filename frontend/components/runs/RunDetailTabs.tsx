'use client'

import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ChartContainer } from '@/components/domain/ChartContainer'
import { StatTile } from '@/components/domain/StatTile'
import { RunSummaryGrid } from '@/components/runs/RunSummaryGrid'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import { DrawdownChart } from '@/components/charts/DrawdownChart'
import { TradeScatterChart } from '@/components/charts/TradeScatterChart'
import { SignalsTable } from '@/components/runs/SignalsTable'
import { FillsTable } from '@/components/runs/FillsTable'
import { TradesTable } from '@/components/runs/TradesTable'
import { formatPercentFromRatio, formatDecimal } from '@/lib/formatters'
import type { BacktestRunStatusDTO, TradeAnalyticsResponse } from '@/lib/api/types'

interface RunDetailTabsProps {
  run: BacktestRunStatusDTO
  analytics: TradeAnalyticsResponse | undefined
}

export function RunDetailTabs({ run, analytics }: RunDetailTabsProps) {
  const result = run.result

  if (!result) return null

  return (
    <Tabs defaultValue="summary">
      <TabsList>
        <TabsTrigger value="summary">Summary</TabsTrigger>
        <TabsTrigger value="charts">Charts</TabsTrigger>
        <TabsTrigger value="trades">Trades</TabsTrigger>
        <TabsTrigger value="signals">Signals</TabsTrigger>
      </TabsList>

      <TabsContent value="summary">
        <div className="space-y-4">
          <RunSummaryGrid result={result} startedAt={run.started_at} finishedAt={run.finished_at} />
          {analytics ? (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
              <StatTile label="Trades" value={String(analytics.stats.trade_count)} />
              <StatTile label="Win Rate" value={formatPercentFromRatio(analytics.stats.win_rate)} />
              <StatTile label="Risk/Reward" value={formatDecimal(analytics.stats.risk_reward_ratio)} />
              <StatTile label="Max Drawdown" value={formatPercentFromRatio(analytics.stats.max_drawdown)} trend="down" />
              <StatTile label="Avg Hold (s)" value={String(analytics.stats.average_time_in_market_seconds ?? '–')} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Analytics not available for this run.</p>
          )}
        </div>
      </TabsContent>

      <TabsContent value="charts">
        <div className="space-y-4">
          <ChartContainer loading={false} empty={result.equity_curve.length === 0}>
            <EquityCurveChart data={result.equity_curve} />
          </ChartContainer>
          <ChartContainer loading={false} empty={result.drawdown_curve.length === 0}>
            <DrawdownChart data={result.drawdown_curve} />
          </ChartContainer>
          {analytics ? (
            <TradeScatterChart trades={analytics.trades} />
          ) : (
            <p className="text-sm text-muted-foreground">Trade scatter chart requires analytics data.</p>
          )}
        </div>
      </TabsContent>

      <TabsContent value="trades">
        {analytics ? (
          <div className="space-y-4">
            <TradesTable trades={analytics.trades} />
            <FillsTable events={[...(result.orders ?? []), ...(result.risk_rejections ?? [])]} />
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">Trade data requires analytics to be available.</p>
            <FillsTable events={[...(result.orders ?? []), ...(result.risk_rejections ?? [])]} />
          </div>
        )}
      </TabsContent>

      <TabsContent value="signals">
        <SignalsTable signals={result.signals} />
      </TabsContent>
    </Tabs>
  )
}
