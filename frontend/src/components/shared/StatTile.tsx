import { cn } from '@/lib/utils'

interface StatTileProps {
  label: string
  value: string
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

export function StatTile({ label, value, trend, className }: StatTileProps) {
  return (
    <div className={cn('rounded-lg border border-zinc-800 bg-zinc-900 p-3', className)}>
      <p className="text-xs text-zinc-400">{label}</p>
      <p
        className={cn(
          'mt-1 text-lg font-semibold',
          trend === 'up' && 'text-green-400',
          trend === 'down' && 'text-red-400',
          !trend && 'text-zinc-100',
        )}
      >
        {value}
      </p>
    </div>
  )
}
