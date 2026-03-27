import { Badge } from '@/components/ui/badge'

const STATE_VARIANT: Record<string, 'bull' | 'bear' | 'warn' | 'info' | 'muted'> = {
  RUNNING: 'bull',
  PAUSED: 'warn',
  EMERGENCY: 'bear',
  INIT: 'muted',
  UNKNOWN: 'muted',
}

export function StatusBadge({ state }: { state: string }) {
  const variant = STATE_VARIANT[state?.toUpperCase()] ?? 'muted'
  return <Badge variant={variant}>{state || 'UNKNOWN'}</Badge>
}
