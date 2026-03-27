import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { EventRecord } from '@/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function SignalsTable({ signals }: { signals: EventRecord[] }) {
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
        {signals.length === 0 ? (
          <TableRow><TableCell colSpan={3} className="text-center text-zinc-500">No signals.</TableCell></TableRow>
        ) : (
          signals.map((s, i) => (
            <TableRow key={i}>
              <TableCell className="font-mono text-xs">{formatUtcTimestamp(s.timestamp)}</TableCell>
              <TableCell>{s.event}</TableCell>
              <TableCell className="font-mono text-xs text-zinc-400">
                {Object.entries(s.payload || {}).map(([k, v]) => `${k}=${v}`).join(' ')}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}
