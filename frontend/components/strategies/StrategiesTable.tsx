'use client'

import { DataTable, type Column } from '@/components/domain/DataTable'
import type { StrategyProfileDTO } from '@/lib/api/types'

const columns: Column<StrategyProfileDTO>[] = [
  {
    key: 'strategy_id',
    header: 'ID',
    cell: (row) => <span className="font-mono text-xs">{row.strategy_id}</span>,
  },
  {
    key: 'name',
    header: 'Name',
    cell: (row) => <span>{row.name}</span>,
  },
  {
    key: 'pattern_set_id',
    header: 'Pattern Set',
    cell: (row) => <span className="font-mono text-xs">{row.strategy.pattern_set_id ?? '–'}</span>,
  },
  {
    key: 'trade_quantity',
    header: 'Trade Qty',
    cell: (row) => <span className="tabular-nums">{row.strategy.trade_quantity ?? '–'}</span>,
  },
]

export function StrategiesTable({ strategies }: { strategies: StrategyProfileDTO[] }) {
  return (
    <DataTable
      columns={columns}
      data={strategies}
      keyExtractor={(row) => row.strategy_id}
      emptyMessage="No strategies."
    />
  )
}
