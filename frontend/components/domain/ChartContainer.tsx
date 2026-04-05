'use client'

import { cn } from '@/lib/utils'

interface ChartContainerProps {
  title?: string
  loading?: boolean
  empty?: boolean
  emptyMessage?: string
  error?: string
  children: React.ReactNode
  className?: string
}

export function ChartContainer({
  title,
  loading = false,
  empty = false,
  emptyMessage = 'No data available.',
  error,
  children,
  className,
}: ChartContainerProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {title && <h3 className="text-sm font-medium">{title}</h3>}
      {error ? (
        <div className="flex items-center justify-center rounded border border-border bg-card py-12">
          <p className="text-sm text-danger">{error}</p>
        </div>
      ) : loading ? (
        <div className="flex items-center justify-center rounded border border-border bg-card py-12">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-foreground" />
        </div>
      ) : empty ? (
        <div className="flex items-center justify-center rounded border border-border bg-card py-12">
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        </div>
      ) : (
        <div className="rounded border border-border bg-card p-4">
          {children}
        </div>
      )}
    </div>
  )
}
