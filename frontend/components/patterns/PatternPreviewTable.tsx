'use client'

import { DataTable, type Column } from '@/components/domain/DataTable'
import type { PatternDTO } from '@/lib/api/types'

const columns: Column<PatternDTO>[] = [
  {
    key: 'label',
    header: 'Label',
    cell: (row) => <span>{row.label}</span>,
  },
  {
    key: 'lookback',
    header: 'Lookback',
    cell: (row) => <span className="tabular-nums">{row.lookback}</span>,
  },
  {
    key: 'sample_size',
    header: 'Sample Size',
    cell: (row) => <span className="tabular-nums">{row.sample_size}</span>,
  },
  {
    key: 'threshold',
    header: 'Threshold',
    cell: (row) => <span className="tabular-nums">{row.threshold}</span>,
  },
]

export function PatternPreviewTable({ patterns }: { patterns: PatternDTO[] }) {
  return (
    <DataTable
      columns={columns}
      data={patterns}
      keyExtractor={(row) => `${row.label}-${row.lookback}`}
      emptyMessage="No patterns."
    />
  )
}
