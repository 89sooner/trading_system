'use client'

import { DataTable, type Column } from '@/components/domain/DataTable'
import type { Trade } from '@/lib/api/types'
import { formatUtcTimestamp, formatDecimal } from '@/lib/formatters'
import { cn } from '@/lib/utils'

const columns: Column<Trade>[] = [
  {
    key: 'entry_time',
    header: 'Entry',
    cell: (row) => <span className="font-mono text-xs">{formatUtcTimestamp(row.entry_time)}</span>,
  },
  {
    key: 'exit_time',
    header: 'Exit',
    cell: (row) => <span className="font-mono text-xs">{formatUtcTimestamp(row.exit_time)}</span>,
  },
  {
    key: 'symbol',
    header: 'Symbol',
    cell: (row) => <span className="font-mono">{row.symbol}</span>,
  },
  {
    key: 'quantity',
    header: 'Qty',
    cell: (row) => <span className="tabular-nums">{row.quantity}</span>,
  },
  {
    key: 'entry_price',
    header: 'Entry $',
    cell: (row) => <span className="tabular-nums">{formatDecimal(row.entry_price)}</span>,
  },
  {
    key: 'exit_price',
    header: 'Exit $',
    cell: (row) => <span className="tabular-nums">{formatDecimal(row.exit_price)}</span>,
  },
  {
    key: 'pnl',
    header: 'PnL',
    cell: (row) => {
      const pnl = Number(row.pnl)
      return (
        <span className={cn('tabular-nums', pnl >= 0 ? 'text-success' : 'text-danger')}>
          {formatDecimal(row.pnl)}
        </span>
      )
    },
  },
  {
    key: 'holding_seconds',
    header: 'Hold (s)',
    cell: (row) => <span className="tabular-nums">{row.holding_seconds}</span>,
  },
]

export function TradesTable({ trades }: { trades: Trade[] }) {
  return (
    <DataTable
      columns={columns}
      data={trades}
      keyExtractor={(row) => `${row.entry_time}-${row.symbol}`}
      emptyMessage="No trades."
    />
  )
}
