'use client'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: string | number
  previousValue?: string | number
  trend?: 'up' | 'down' | 'neutral'
  format?: 'currency' | 'percent' | 'number' | 'text'
  loading?: boolean
  className?: string
}

export function MetricCard({
  label,
  value,
  previousValue,
  trend,
  loading = false,
  className,
}: MetricCardProps) {
  if (loading) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="p-4">
          <div className="space-y-2">
            <div className="h-3 w-20 animate-pulse rounded bg-muted" />
            <div className="h-6 w-28 animate-pulse rounded bg-muted" />
            <div className="h-3 w-16 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-danger' : 'text-muted-foreground'

  return (
    <Card className={cn('', className)}>
      <CardContent className="p-4">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-semibold tabular-nums tracking-tight font-mono">
          {value}
        </p>
        {(trend || previousValue !== undefined) && (
          <div className={cn('mt-1 flex items-center gap-1 text-xs', trendColor)}>
            {trend && <TrendIcon className="h-3 w-3" />}
            {previousValue !== undefined && <span>{previousValue}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
