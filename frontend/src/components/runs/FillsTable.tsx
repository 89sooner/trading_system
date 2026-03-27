import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { EventRecord } from '@/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function FillsTable({ events }: { events: EventRecord[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Time</TableHead>
          <TableHead>Event</TableHead>
          <TableHead>Payload</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {events.length === 0 ? (
          <TableRow><TableCell colSpan={3} className="text-center text-zinc-500">No fills or rejections.</TableCell></TableRow>
        ) : (
          events.map((e, i) => (
            <TableRow key={i} className={e.event.includes('reject') ? 'opacity-60' : ''}>
              <TableCell className="font-mono text-xs">{formatUtcTimestamp(e.timestamp)}</TableCell>
              <TableCell className={e.event.includes('reject') ? 'text-red-400' : ''}>{e.event}</TableCell>
              <TableCell className="font-mono text-xs text-zinc-400">
                {Object.entries(e.payload || {}).map(([k, v]) => `${k}=${v}`).join(' ')}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}
