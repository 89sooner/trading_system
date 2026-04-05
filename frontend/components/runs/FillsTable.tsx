'use client'

import { DataTable, type Column } from '@/components/domain/DataTable'
import type { EventRecord } from '@/lib/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'
import { cn } from '@/lib/utils'

const columns: Column<EventRecord>[] = [
  {
    key: 'timestamp',
    header: 'Time',
    cell: (row) => <span className="font-mono text-xs">{formatUtcTimestamp(row.timestamp)}</span>,
  },
  {
    key: 'event',
    header: 'Event',
    cell: (row) => (
      <span className={cn(row.event.includes('reject') && 'text-danger')}>{row.event}</span>
    ),
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

export function FillsTable({ events }: { events: EventRecord[] }) {
  return (
    <DataTable
      columns={columns}
      data={events}
      keyExtractor={(row) => `${row.timestamp}-${row.event}`}
      emptyMessage="No fills or rejections."
    />
  )
}
