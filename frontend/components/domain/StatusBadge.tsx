import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

const stateStyles: Record<string, string> = {
  queued: 'bg-warning/15 text-warning border-warning/30',
  succeeded: 'bg-success/15 text-success border-success/30',
  failed: 'bg-danger/15 text-danger border-danger/30',
  cancelled: 'bg-muted text-muted-foreground border-border',
  running: 'bg-info/15 text-info border-info/30',
  pending: 'bg-warning/15 text-warning border-warning/30',
}

export function StatusBadge({ state }: { state: string }) {
  return (
    <Badge variant="outline" className={cn('text-xs font-medium', stateStyles[state])}>
      {state}
    </Badge>
  )
}
