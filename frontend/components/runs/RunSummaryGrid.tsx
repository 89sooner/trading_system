'use client'

import { StatTile } from '@/components/domain/StatTile'
import { formatPercentFromRatio, formatDecimal, formatUtcTimestamp } from '@/lib/formatters'
import type { BacktestResult } from '@/lib/api/types'

export function RunSummaryGrid({ result, startedAt, finishedAt }: { result: BacktestResult; startedAt: string; finishedAt: string }) {
  const returnVal = Number(result.summary.return)
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      <StatTile label="Return" value={formatPercentFromRatio(result.summary.return)} trend={returnVal >= 0 ? 'up' : 'down'} />
      <StatTile label="Max Drawdown" value={formatPercentFromRatio(result.summary.max_drawdown)} trend="down" />
      <StatTile label="Volatility" value={formatDecimal(result.summary.volatility)} />
      <StatTile label="Win Rate" value={formatPercentFromRatio(result.summary.win_rate)} />
      <StatTile label="Started" value={formatUtcTimestamp(startedAt)} />
      <StatTile label="Finished" value={formatUtcTimestamp(finishedAt)} />
    </div>
  )
}
