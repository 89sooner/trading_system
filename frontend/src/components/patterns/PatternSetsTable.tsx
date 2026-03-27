import { Link } from '@tanstack/react-router'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { PatternSetDTO } from '@/api/types'

export function PatternSetsTable({ patternSets }: { patternSets: PatternSetDTO[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Symbol</TableHead>
          <TableHead>Patterns</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {patternSets.length === 0 ? (
          <TableRow><TableCell colSpan={5} className="text-center text-zinc-500">No saved patterns.</TableCell></TableRow>
        ) : (
          patternSets.map((ps) => (
            <TableRow key={ps.pattern_set_id}>
              <TableCell className="font-mono text-xs">{ps.pattern_set_id}</TableCell>
              <TableCell>{ps.name}</TableCell>
              <TableCell>{ps.symbol}</TableCell>
              <TableCell>{ps.patterns.length}</TableCell>
              <TableCell>
                <Link to="/patterns/$patternSetId" params={{ patternSetId: ps.pattern_set_id }} className="text-xs text-blue-400 hover:underline">
                  Open
                </Link>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}
