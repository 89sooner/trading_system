'use client'

import { DataTable, type Column } from '@/components/domain/DataTable'
import type { EventRecord } from '@/lib/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

const columns: Column<EventRecord>[] = [
  {
    key: 'timestamp',
    header: 'Time',
    cell: (row) => <span className="font-mono text-xs">{formatUtcTimestamp(row.timestamp)}</span>,
  },
  {
    key: 'event',
    header: 'Event',
    cell: (row) => <span>{row.event}</span>,
  },
  {
    key: 'payload',
    header: 'Payload',
    cell: (row) => (
      <span className="font-mono text-xs text-muted-foreground">
        {Object.entries(row.payload || {}).map(([k, v]) => `${k}=${v}`).join(' ')}
      </span>
    ),
  },
]

export function SignalsTable({ signals }: { signals: EventRecord[] }) {
  return (
    <DataTable
      columns={columns}
      data={signals}
      keyExtractor={(row) => `${row.timestamp}-${row.event}`}
      emptyMessage="No signals."
    />
  )
}
