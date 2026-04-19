'use client'

import { DataTable, type Column } from '@/components/domain/DataTable'
import type { Position, PositionsResponse } from '@/lib/api/types'
import { cn } from '@/lib/utils'

const columns: Column<Position>[] = [
  {
    key: 'symbol',
    header: 'Symbol',
    cell: (row) => <span className="font-mono text-sm">{row.symbol}</span>,
  },
  {
    key: 'quantity',
    header: 'Qty',
    cell: (row) => <span className="font-mono tabular-nums">{row.quantity}</span>,
  },
  {
    key: 'average_cost',
    header: 'Avg Cost',
    cell: (row) => <span className="font-mono tabular-nums">{row.average_cost}</span>,
  },
  {
    key: 'unrealized_pnl',
    header: 'Unrealized P&L',
    cell: (row) => {
      const pnl = Number(row.unrealized_pnl)
      return (
        <span
          className={cn(
            'font-mono tabular-nums',
            row.unrealized_pnl == null
              ? 'text-muted-foreground'
              : pnl >= 0
                ? 'text-success'
                : 'text-danger',
          )}
        >
          {row.unrealized_pnl ?? '-'}
        </span>
      )
    },
  },
]

interface PositionsPanelProps {
  data: PositionsResponse | undefined
  loading: boolean
}

export function PositionsPanel({ data, loading }: PositionsPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between rounded-xl border border-border/80 bg-muted/20 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Open positions
        </span>
        {data && (
          <span className="text-xs text-muted-foreground">
            Cash: <span className="font-mono text-foreground">{data.cash}</span>
          </span>
        )}
      </div>
      <DataTable
        columns={columns}
        data={data?.positions ?? []}
        keyExtractor={(p) => p.symbol}
        loading={loading}
        emptyMessage="No open positions."
      />
    </div>
  )
}
