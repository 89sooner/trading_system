'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Filter, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { DashboardPanel } from '@/components/dashboard/DashboardPanel'
import { EquityChart, type EquityDataPoint } from '@/components/dashboard/EquityChart'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { PageHeader } from '@/components/layout/PageHeader'
import {
  exportLiveRuntimeSessions,
  exportLiveSessionOrderAudit,
  getLiveRuntimeSessionEquity,
  getLiveRuntimeSessionEvidence,
  listLiveRuntimeSessions,
} from '@/lib/api/dashboard'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { LiveRuntimeSessionEvidence, LiveRuntimeSessionRecord, LiveRuntimeSessionSearchParams } from '@/lib/api/types'

const SESSION_PAGE_SIZE = 25

const columns: Column<LiveRuntimeSessionRecord>[] = [
  {
    key: 'session',
    header: 'Session',
    cell: (row) => <span className="font-mono text-xs">{row.session_id}</span>,
  },
  {
    key: 'route',
    header: 'Route',
    cell: (row) => (
      <span className="text-xs text-muted-foreground">
        {row.provider} / {row.broker} / {row.live_execution}
      </span>
    ),
  },
  {
    key: 'state',
    header: 'State',
    cell: (row) => (
      <Badge variant={row.last_error ? 'destructive' : 'outline'}>{row.last_state}</Badge>
    ),
  },
  {
    key: 'symbols',
    header: 'Symbols',
    cell: (row) => (
      <div className="flex flex-wrap gap-1">
        {row.symbols.map((symbol) => (
          <Badge key={symbol} variant="secondary">
            {symbol}
          </Badge>
        ))}
      </div>
    ),
  },
  {
    key: 'started',
    header: 'Started',
    cell: (row) => <span className="text-xs">{formatUtcTimestamp(row.started_at)}</span>,
  },
]

interface Filters {
  start: string
  end: string
  provider: string
  broker: string
  liveExecution: string
  state: string
  symbol: string
  hasError: string
}

const defaultFilters: Filters = {
  start: '',
  end: '',
  provider: 'all',
  broker: 'all',
  liveExecution: 'all',
  state: 'all',
  symbol: '',
  hasError: 'all',
}

function toQueryParams(filters: Filters): LiveRuntimeSessionSearchParams {
  return {
    page: 1,
    page_size: SESSION_PAGE_SIZE,
    start: filters.start ? `${filters.start}T00:00:00Z` : undefined,
    end: filters.end ? `${filters.end}T23:59:59Z` : undefined,
    provider: filters.provider === 'all' ? undefined : filters.provider,
    broker: filters.broker === 'all' ? undefined : filters.broker,
    live_execution: filters.liveExecution === 'all' ? undefined : filters.liveExecution,
    state: filters.state === 'all' ? undefined : filters.state,
    symbol: filters.symbol.trim() || undefined,
    has_error: filters.hasError === 'all' ? undefined : filters.hasError === 'true',
    sort: 'desc',
  }
}

async function downloadText(body: string, filename: string, contentType: string) {
  const blob = new Blob([body], { type: contentType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export default function DashboardSessionsPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const queryParams = toQueryParams(filters)

  const sessionsQuery = useQuery({
    queryKey: ['live-runtime', 'sessions', queryParams],
    queryFn: () => listLiveRuntimeSessions(queryParams),
    staleTime: 15_000,
    retry: 1,
  })

  const evidenceQuery = useQuery({
    queryKey: ['live-runtime', 'session-evidence', selectedSessionId],
    queryFn: () => getLiveRuntimeSessionEvidence(selectedSessionId as string),
    enabled: selectedSessionId != null,
    staleTime: 15_000,
    retry: 1,
  })

  const equityQuery = useQuery({
    queryKey: ['live-runtime', 'session-equity', selectedSessionId],
    queryFn: () => getLiveRuntimeSessionEquity(selectedSessionId as string),
    enabled: selectedSessionId != null,
    staleTime: 15_000,
    retry: 1,
  })

  const sessions = sessionsQuery.data?.sessions ?? []
  const selectedSession =
    evidenceQuery.data?.session ?? sessions.find((session) => session.session_id === selectedSessionId)

  async function exportSessions(format: 'csv' | 'jsonl') {
    const body = await exportLiveRuntimeSessions({ ...queryParams, format, limit: 5000 })
    await downloadText(
      body,
      `live-sessions.${format === 'csv' ? 'csv' : 'jsonl'}`,
      format === 'csv' ? 'text/csv' : 'application/x-ndjson',
    )
  }

  async function exportAudit() {
    if (!selectedSessionId) return
    const body = await exportLiveSessionOrderAudit({
      owner_id: selectedSessionId,
      format: 'csv',
      limit: 5000,
    })
    await downloadText(body, `${selectedSessionId}-order-audit.csv`, 'text/csv')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Sessions"
        description="Search historical runtime sessions and collect session-level evidence for incident review."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => sessionsQuery.refetch()}>
              <RefreshCw />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={() => exportSessions('csv')}>
              <Download />
              CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => exportSessions('jsonl')}>
              <Download />
              JSONL
            </Button>
          </div>
        }
      />

      <DashboardPanel
        eyebrow="Search"
        title="Session filters"
        description="Filter durable live runtime sessions by route, state, symbol, time range, and error status."
        action={<Filter className="h-4 w-4 text-muted-foreground" />}
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <FilterInput
            label="Start date"
            type="date"
            value={filters.start}
            onChange={(value) => setFilters((current) => ({ ...current, start: value }))}
          />
          <FilterInput
            label="End date"
            type="date"
            value={filters.end}
            onChange={(value) => setFilters((current) => ({ ...current, end: value }))}
          />
          <FilterInput
            label="Symbol"
            value={filters.symbol}
            placeholder="005930"
            onChange={(value) => setFilters((current) => ({ ...current, symbol: value }))}
          />
          <FilterSelect
            label="Provider"
            value={filters.provider}
            values={['all', 'mock', 'csv', 'kis']}
            onChange={(value) => setFilters((current) => ({ ...current, provider: value }))}
          />
          <FilterSelect
            label="Broker"
            value={filters.broker}
            values={['all', 'paper', 'kis']}
            onChange={(value) => setFilters((current) => ({ ...current, broker: value }))}
          />
          <FilterSelect
            label="Execution"
            value={filters.liveExecution}
            values={['all', 'paper', 'live']}
            onChange={(value) => setFilters((current) => ({ ...current, liveExecution: value }))}
          />
          <FilterSelect
            label="State"
            value={filters.state}
            values={['all', 'starting', 'running', 'paused', 'stopped', 'emergency', 'error']}
            onChange={(value) => setFilters((current) => ({ ...current, state: value }))}
          />
          <FilterSelect
            label="Error"
            value={filters.hasError}
            values={['all', 'true', 'false']}
            labels={{ all: 'all', true: 'with error', false: 'no error' }}
            onChange={(value) => setFilters((current) => ({ ...current, hasError: value }))}
          />
        </div>
      </DashboardPanel>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.9fr)]">
        <DashboardPanel
          eyebrow="History"
          title="Session results"
          description={`${sessionsQuery.data?.total ?? 0} session(s) match the current filters.`}
        >
          {sessionsQuery.isError ? (
            <div className="rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm">
              Session history could not be loaded.
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={sessions}
              keyExtractor={(row) => row.session_id}
              loading={sessionsQuery.isLoading}
              loadingRows={5}
              emptyMessage="No live runtime sessions match the current filters."
              onRowClick={(row) => setSelectedSessionId(row.session_id)}
            />
          )}
        </DashboardPanel>

        <SessionEvidencePanel
          session={selectedSession ?? null}
          evidence={evidenceQuery.data ?? null}
          equity={(equityQuery.data?.points ?? []).map((point) => ({
            time: new Date(point.timestamp).getTime(),
            value: Number(point.equity),
          }))}
          loading={evidenceQuery.isLoading || equityQuery.isLoading}
          onExportAudit={exportAudit}
        />
      </div>
    </div>
  )
}

function FilterInput({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  placeholder?: string
}) {
  const id = `session-filter-${label.toLowerCase().replace(/\s+/g, '-')}`
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function FilterSelect({
  label,
  value,
  values,
  labels,
  onChange,
}: {
  label: string
  value: string
  values: string[]
  labels?: Record<string, string>
  onChange: (value: string) => void
}) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Select value={value} onValueChange={(nextValue) => {
        if (nextValue != null) onChange(nextValue)
      }}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {values.map((item) => (
            <SelectItem key={item} value={item}>
              {labels?.[item] ?? item}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function SessionEvidencePanel({
  session,
  evidence,
  equity,
  loading,
  onExportAudit,
}: {
  session: LiveRuntimeSessionRecord | null
  evidence: LiveRuntimeSessionEvidence | null
  equity: EquityDataPoint[]
  loading: boolean
  onExportAudit: () => void
}) {
  return (
    <DashboardPanel
      eyebrow="Evidence"
      title="Session detail"
      description="Session evidence combines preflight, equity, archived incidents, and order audit records."
      action={
        session ? (
          <Button variant="outline" size="sm" onClick={onExportAudit}>
            <Download />
            Audit CSV
          </Button>
        ) : null
      }
    >
      {!session ? (
        <div className="rounded-xl border border-border/80 bg-muted/20 p-6 text-sm text-muted-foreground">
          Select a session row to review its evidence.
        </div>
      ) : loading ? (
        <div className="flex min-h-52 items-center justify-center rounded-xl border border-border/80 bg-muted/20">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <InfoTile label="Session" value={session.session_id} />
            <InfoTile label="Route" value={`${session.provider} / ${session.broker}`} />
            <InfoTile label="Execution" value={session.live_execution} />
            <InfoTile label="State" value={session.last_state} />
          </div>

          <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={session.preflight_summary?.ready ? 'default' : 'outline'}>
                {session.preflight_summary?.ready ? 'preflight ready' : 'preflight unknown'}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {session.preflight_summary?.checked_at
                  ? formatUtcTimestamp(session.preflight_summary.checked_at)
                  : 'not recorded'}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {session.preflight_summary?.message ?? 'No preflight message was recorded.'}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <InfoTile label="Audit records" value={String(evidence?.order_audit_count ?? 0)} />
            <InfoTile label="Archived events" value={String(evidence?.archived_event_count ?? 0)} />
            <InfoTile label="Equity points" value={String(evidence?.equity_point_count ?? 0)} />
          </div>

          {equity.length > 0 ? (
            <div className="rounded-xl border border-border/80 bg-background p-4">
              <EquityChart data={equity} />
            </div>
          ) : (
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4 text-sm text-muted-foreground">
              No historical equity points are available for this session.
            </div>
          )}

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Incident timeline
            </p>
            {(evidence?.recent_archived_events ?? []).length > 0 ? (
              <div className="space-y-2">
                {evidence?.recent_archived_events.map((event) => (
                  <div key={event.record_id} className="rounded-xl border border-border/80 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={event.severity === 'ERROR' ? 'destructive' : 'secondary'}>
                        {event.severity}
                      </Badge>
                      <span className="font-mono text-xs">{event.event}</span>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {formatUtcTimestamp(event.timestamp)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No archived incident events are available for this session.
              </p>
            )}
          </div>
        </div>
      )}
    </DashboardPanel>
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
