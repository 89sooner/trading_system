'use client'

import type { ReactNode } from 'react'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface SurfacePanelProps {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
}

export function SurfacePanel({
  eyebrow,
  title,
  description,
  action,
  children,
  className,
  contentClassName,
}: SurfacePanelProps) {
  return (
    <Card
      className={cn(
        'border-none bg-card shadow-[0_1px_2px_rgba(15,23,42,0.05),0_12px_30px_rgba(15,23,42,0.06)] ring-1 ring-slate-950/8',
        className,
      )}
    >
      <CardHeader>
        {action ? <CardAction>{action}</CardAction> : null}
        {eyebrow ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {eyebrow}
          </p>
        ) : null}
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent className={cn('space-y-4', contentClassName)}>{children}</CardContent>
    </Card>
  )
}
