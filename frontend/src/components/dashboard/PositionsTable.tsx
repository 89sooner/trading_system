import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { PositionsResponse } from '@/api/types'

export function PositionsTable({ data }: { data: PositionsResponse }) {
  return (
    <div>
      <div className="mb-2 text-xs text-zinc-400">
        Cash: <span className="font-semibold text-zinc-100">{data.cash}</span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Avg Cost</TableHead>
            <TableHead>Unrealized PnL</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.positions.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-zinc-500">
                No open positions.
              </TableCell>
            </TableRow>
          ) : (
            data.positions.map((p) => (
              <TableRow key={p.symbol}>
                <TableCell className="font-mono">{p.symbol}</TableCell>
                <TableCell>{p.quantity}</TableCell>
                <TableCell>{p.average_cost}</TableCell>
                <TableCell
                  className={
                    p.unrealized_pnl == null
                      ? 'text-zinc-500'
                      : Number(p.unrealized_pnl) >= 0
                      ? 'text-green-400'
                      : 'text-red-400'
                  }
                >
                  {p.unrealized_pnl ?? '-'}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
