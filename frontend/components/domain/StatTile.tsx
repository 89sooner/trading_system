import { cn } from '@/lib/utils'

interface StatTileProps {
  label: string
  value: string
  trend?: 'up' | 'down'
}

export function StatTile({ label, value, trend }: StatTileProps) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={cn(
          'mt-0.5 font-mono text-sm font-semibold tabular-nums',
          trend === 'up' && 'text-success',
          trend === 'down' && 'text-danger',
        )}
      >
        {value}
      </p>
    </div>
  )
}
