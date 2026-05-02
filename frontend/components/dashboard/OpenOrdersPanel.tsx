'use client'

import { Ban } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { postDashboardOrderCancel } from '@/lib/api/dashboard'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { LiveOrderRecord, LiveOrderList } from '@/lib/api/types'

const terminalStatuses = new Set(['filled', 'rejected', 'cancelled'])

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'stale' || status === 'unknown') return 'destructive'
  if (status === 'cancel_requested') return 'secondary'
  if (terminalStatuses.has(status)) return 'outline'
  return 'default'
}

interface OpenOrdersPanelProps {
  data: LiveOrderList | undefined
  loading: boolean
}

export function OpenOrdersPanel({ data, loading }: OpenOrdersPanelProps) {
  const queryClient = useQueryClient()
  const cancelMutation = useMutation({
    mutationFn: postDashboardOrderCancel,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'orders'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard', 'events'] })
    },
  })

  const columns: Column<LiveOrderRecord>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      cell: (row) => <span className="font-mono text-sm">{row.symbol}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      cell: (row) => <Badge variant={statusVariant(row.status)}>{row.status}</Badge>,
    },
    {
      key: 'remaining',
      header: 'Remaining',
      cell: (row) => (
        <span className="font-mono tabular-nums">
          {row.remaining_quantity}/{row.requested_quantity}
        </span>
      ),
    },
    {
      key: 'broker_order_id',
      header: 'Broker ID',
      cell: (row) => (
        <span className="font-mono text-xs text-muted-foreground">
          {row.broker_order_id ?? '-'}
        </span>
      ),
    },
    {
      key: 'last_synced_at',
      header: 'Last Sync',
      cell: (row) => (
        <span className="text-xs text-muted-foreground">
          {row.last_synced_at ? formatUtcTimestamp(row.last_synced_at) : '-'}
        </span>
      ),
    },
    {
      key: 'action',
      header: '',
      className: 'w-20 text-right',
      cell: (row) => {
        const disabled =
          terminalStatuses.has(row.status)
          || row.status === 'cancel_requested'
          || cancelMutation.isPending
        return (
          <Button
            type="button"
            variant="destructive"
            size="icon-sm"
            disabled={disabled}
            aria-label={`Cancel order ${row.record_id}`}
            onClick={(event) => {
              event.stopPropagation()
              cancelMutation.mutate(row.record_id)
            }}
          >
            <Ban className="h-3.5 w-3.5" />
          </Button>
        )
      },
    },
  ]

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between rounded-xl border border-border/80 bg-muted/20 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Active broker orders
        </span>
        <span className="text-xs text-muted-foreground">
          Total: <span className="font-mono text-foreground">{data?.total ?? 0}</span>
        </span>
      </div>
      <DataTable
        columns={columns}
        data={data?.orders ?? []}
        keyExtractor={(order) => order.record_id}
        loading={loading}
        emptyMessage="No active broker orders."
      />
      {cancelMutation.data?.message ? (
        <p className="text-xs text-muted-foreground">{cancelMutation.data.message}</p>
      ) : null}
      {cancelMutation.error ? (
        <p className="text-xs text-danger">Cancel request failed.</p>
      ) : null}
    </div>
  )
}
