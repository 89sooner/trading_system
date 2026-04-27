'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { exportLiveSessionOrderAudit } from '@/lib/api/dashboard'
import { formatUtcTimestamp } from '@/lib/formatters'
import { Download } from 'lucide-react'
import type { LiveRuntimeSessionRecord } from '@/lib/api/types'

interface SessionDetailDialogProps {
  session: LiveRuntimeSessionRecord | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SessionDetailDialog({
  session,
  open,
  onOpenChange,
}: SessionDetailDialogProps) {
  const preflight = session?.preflight_summary
  const handleExportAudit = async () => {
    if (!session) return
    const body = await exportLiveSessionOrderAudit({
      owner_id: session.session_id,
      format: 'csv',
      limit: 5000,
    })
    const blob = new Blob([body], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${session.session_id}-order-audit.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <DialogTitle>Session detail</DialogTitle>
              <DialogDescription>
                {session ? session.session_id : 'No session selected.'}
              </DialogDescription>
            </div>
            {session ? (
              <Button variant="outline" size="sm" onClick={handleExportAudit}>
                <Download aria-hidden="true" />
                Export audit CSV
              </Button>
            ) : null}
          </div>
        </DialogHeader>

        {session ? (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <InfoTile label="Started" value={formatUtcTimestamp(session.started_at)} />
              <InfoTile
                label="Ended"
                value={session.ended_at ? formatUtcTimestamp(session.ended_at) : 'active'}
              />
              <InfoTile
                label="Route"
                value={`${session.provider} / ${session.broker} / ${session.live_execution}`}
              />
              <InfoTile label="Final state" value={session.last_state} />
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Symbols
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {session.symbols.map((symbol) => (
                  <Badge key={symbol} variant="outline">
                    {symbol}
                  </Badge>
                ))}
              </div>
            </div>

            {session.last_error ? (
              <div className="rounded-xl border border-danger/20 bg-danger/10 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-danger">
                  Last error
                </p>
                <p className="mt-2 text-sm">{session.last_error}</p>
              </div>
            ) : null}

            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Preflight
                </p>
                {preflight ? (
                  <Badge variant={preflight.ready ? 'default' : 'destructive'}>
                    {preflight.ready ? 'ready' : 'blocked'}
                  </Badge>
                ) : (
                  <Badge variant="outline">not recorded</Badge>
                )}
              </div>
              {preflight ? (
                <div className="mt-3 space-y-3">
                  <p className="text-sm leading-6 text-muted-foreground">
                    {preflight.message ?? 'No preflight message recorded.'}
                  </p>
                  <BadgeList
                    label="Blocking reasons"
                    values={preflight.blocking_reasons ?? []}
                    destructive
                  />
                  <BadgeList label="Warnings" values={preflight.warnings ?? []} />
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-medium">{value}</p>
    </div>
  )
}

function BadgeList({
  label,
  values,
  destructive = false,
}: {
  label: string
  values: string[]
  destructive?: boolean
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.length > 0 ? (
          values.map((value) => (
            <Badge key={value} variant={destructive ? 'destructive' : 'secondary'}>
              {value}
            </Badge>
          ))
        ) : (
          <Badge variant="outline">none</Badge>
        )}
      </div>
    </div>
  )
}
