import { cn } from '@/lib/utils'

type StatusVariant = 'online' | 'offline' | 'warning' | 'error'

interface StatusIndicatorProps {
  variant: StatusVariant
  label?: string
  className?: string
}

const variantStyles: Record<StatusVariant, { dot: string; text: string }> = {
  online: { dot: 'bg-success', text: 'text-success' },
  offline: { dot: 'bg-muted-foreground', text: 'text-muted-foreground' },
  warning: { dot: 'bg-warning', text: 'text-warning' },
  error: { dot: 'bg-danger', text: 'text-danger' },
}

export function StatusIndicator({ variant, label, className }: StatusIndicatorProps) {
  const style = variantStyles[variant]
  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <span className={cn('inline-block h-2 w-2 rounded-full', style.dot)} />
      {label && <span className={cn('text-xs font-medium', style.text)}>{label}</span>}
    </div>
  )
}
