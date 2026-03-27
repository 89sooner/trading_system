import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { Trade } from '@/api/types'
import { formatUtcTimestamp, formatDecimal } from '@/lib/formatters'

export function TradesTable({ trades }: { trades: Trade[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Entry</TableHead>
          <TableHead>Exit</TableHead>
          <TableHead>Symbol</TableHead>
          <TableHead>Qty</TableHead>
          <TableHead>Entry $</TableHead>
          <TableHead>Exit $</TableHead>
          <TableHead>PnL</TableHead>
          <TableHead>Hold (s)</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.length === 0 ? (
          <TableRow><TableCell colSpan={8} className="text-center text-zinc-500">No trades.</TableCell></TableRow>
        ) : (
          trades.map((t, i) => {
            const pnl = Number(t.pnl)
            return (
              <TableRow key={i}>
                <TableCell className="font-mono text-xs">{formatUtcTimestamp(t.entry_time)}</TableCell>
                <TableCell className="font-mono text-xs">{formatUtcTimestamp(t.exit_time)}</TableCell>
                <TableCell className="font-mono">{t.symbol}</TableCell>
                <TableCell>{t.quantity}</TableCell>
                <TableCell>{formatDecimal(t.entry_price)}</TableCell>
                <TableCell>{formatDecimal(t.exit_price)}</TableCell>
                <TableCell className={pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {formatDecimal(t.pnl)}
                </TableCell>
                <TableCell>{t.holding_seconds}</TableCell>
              </TableRow>
            )
          })
        )}
      </TableBody>
    </Table>
  )
}
