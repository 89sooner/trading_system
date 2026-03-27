import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { PatternDTO } from '@/api/types'

export function PatternPreviewTable({ patterns }: { patterns: PatternDTO[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Label</TableHead>
          <TableHead>Lookback</TableHead>
          <TableHead>Sample Size</TableHead>
          <TableHead>Threshold</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {patterns.map((p, i) => (
          <TableRow key={i}>
            <TableCell>{p.label}</TableCell>
            <TableCell>{p.lookback}</TableCell>
            <TableCell>{p.sample_size}</TableCell>
            <TableCell>{p.threshold}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
