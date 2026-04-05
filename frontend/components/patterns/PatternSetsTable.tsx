'use client'

import Link from 'next/link'
import { DataTable, type Column } from '@/components/domain/DataTable'
import type { PatternSetDTO } from '@/lib/api/types'

const columns: Column<PatternSetDTO>[] = [
  {
    key: 'pattern_set_id',
    header: 'ID',
    cell: (row) => <span className="font-mono text-xs">{row.pattern_set_id}</span>,
  },
  {
    key: 'name',
    header: 'Name',
    cell: (row) => <span>{row.name}</span>,
  },
  {
    key: 'symbol',
    header: 'Symbol',
    cell: (row) => <span className="font-mono">{row.symbol}</span>,
  },
  {
    key: 'patterns',
    header: 'Patterns',
    cell: (row) => <span className="tabular-nums">{row.patterns.length}</span>,
  },
  {
    key: 'actions',
    header: '',
    cell: (row) => (
      <Link href={`/patterns/${row.pattern_set_id}`} className="text-xs text-info hover:underline">
        Open
      </Link>
    ),
  },
]

export function PatternSetsTable({ patternSets }: { patternSets: PatternSetDTO[] }) {
  return (
    <DataTable
      columns={columns}
      data={patternSets}
      keyExtractor={(row) => row.pattern_set_id}
      emptyMessage="No saved patterns."
    />
  )
}
