import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { StrategyProfileDTO } from '@/api/types'

export function StrategiesTable({ strategies }: { strategies: StrategyProfileDTO[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Pattern Set</TableHead>
          <TableHead>Trade Qty</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {strategies.length === 0 ? (
          <TableRow>
            <TableCell colSpan={4} className="text-center text-zinc-500">No strategies.</TableCell>
          </TableRow>
        ) : (
          strategies.map((s) => (
            <TableRow key={s.strategy_id}>
              <TableCell className="font-mono text-xs">{s.strategy_id}</TableCell>
              <TableCell>{s.name}</TableCell>
              <TableCell className="font-mono text-xs">{s.strategy.pattern_set_id ?? '–'}</TableCell>
              <TableCell>{s.strategy.trade_quantity ?? '–'}</TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}
