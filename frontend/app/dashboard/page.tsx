'use client'

import { Activity, ShieldCheck, Siren, TimerReset } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { RuntimeLaunchForm } from '@/components/dashboard/RuntimeLaunchForm'
import { SessionHistoryPanel } from '@/components/dashboard/SessionHistoryPanel'
import { DashboardMetrics } from '@/components/dashboard/DashboardMetrics'
import { DashboardPanel } from '@/components/dashboard/DashboardPanel'
import { ControlButtons } from '@/components/dashboard/ControlButtons'
import { EquityChart } from '@/components/dashboard/EquityChart'
import { EventTimeline } from '@/components/dashboard/EventTimeline'
import { OpenOrdersPanel } from '@/components/dashboard/OpenOrdersPanel'
import { PositionsPanel } from '@/components/dashboard/PositionsPanel'
import { StatusIndicator } from '@/components/domain/StatusIndicator'
import { useDashboardStream } from '@/hooks/useDashboardStream'
import { PageHeader } from '@/components/layout/PageHeader'
import { formatUtcTimestamp, formatUptime } from '@/lib/formatters'

function badgeTone(severity: string): 'secondary' | 'destructive' {
  return severity === 'WARNING' ? 'secondary' : 'destructive'
}

export default function DashboardPage() {
  const {
    statusQuery,
    positionsQuery,
    eventsQuery,
    ordersQuery,
    hasActiveRuntime,
    isLive,
    equitySeries,
    sseConnected,
  } = useDashboardStream()

  const loading = statusQuery.isLoading || (hasActiveRuntime && positionsQuery.isLoading)
  const status = statusQuery.data
  const latestIncident = status?.latest_incident
  const statusLabel = hasActiveRuntime
    ? sseConnected
      ? 'Connected (SSE)'
      : status?.state ?? 'Starting'
    : status?.controller_state === 'error'
      ? 'Controller error'
      : 'Disconnected'

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operations Console"
        description="Preflight, launch, monitor, and recover the live runtime from one consistent operator surface."
        actions={
          <div className="flex flex-col items-end gap-2">
            <StatusIndicator
              variant={
                sseConnected
                  ? 'online'
                  : hasActiveRuntime
                    ? 'warning'
                    : status?.last_error
                      ? 'error'
                      : 'offline'
              }
              label={statusLabel}
            />
            {hasActiveRuntime ? <ControlButtons /> : null}
          </div>
        }
      />

      <DashboardMetrics
        status={status}
        positions={hasActiveRuntime ? positionsQuery.data : undefined}
        isLive={isLive}
        loading={loading}
      />

      {!hasActiveRuntime ? <RuntimeLaunchForm /> : null}
      <SessionHistoryPanel />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.95fr)]">
        <div className="space-y-4">
          <DashboardPanel
            eyebrow="Runtime"
            title="Runtime briefing"
            description="Current controller, attached session, and market posture."
            action={<Activity className="h-4 w-4 text-muted-foreground" />}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Controller
                </p>
                <p className="mt-2 text-sm font-medium">
                  {status?.controller_state ?? 'idle'}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {status?.controller_state_detail ?? 'No runtime session is attached.'}
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Session
                </p>
                <p className="mt-2 text-sm font-medium">
                  {status?.session_id ?? 'none'}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {status?.provider ?? '-'} / {status?.broker ?? '-'} / {status?.live_execution ?? '-'}
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-border/80 bg-background p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Heartbeat
                </p>
                <p className="mt-2 text-sm font-medium">
                  {status?.last_heartbeat ? formatUtcTimestamp(status.last_heartbeat) : '-'}
                </p>
              </div>
              <div className="rounded-xl border border-border/80 bg-background p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Uptime
                </p>
                <p className="mt-2 text-sm font-medium">{formatUptime(status?.uptime_seconds)}</p>
              </div>
              <div className="rounded-xl border border-border/80 bg-background p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Market
                </p>
                <p className="mt-2 text-sm font-medium">{status?.market_session ?? 'n/a'}</p>
              </div>
            </div>

            {status?.symbols && status.symbols.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Active symbols
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {status.symbols.map((symbol) => (
                    <Badge key={symbol} variant="outline">
                      {symbol}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
          </DashboardPanel>

          <div className="grid gap-4 lg:grid-cols-2">
            <DashboardPanel
              eyebrow="Portfolio"
              title="Positions"
              description="Open positions and current cash balance."
            >
              <PositionsPanel
                data={hasActiveRuntime ? positionsQuery.data : undefined}
                loading={hasActiveRuntime ? positionsQuery.isLoading : false}
              />
            </DashboardPanel>

            <DashboardPanel
              eyebrow="Orders"
              title="Open orders"
              description="Active broker orders, lifecycle freshness, and cancel control."
            >
              <OpenOrdersPanel
                data={hasActiveRuntime ? ordersQuery.data : undefined}
                loading={hasActiveRuntime ? ordersQuery.isLoading : false}
              />
            </DashboardPanel>

            <DashboardPanel
              eyebrow="Performance"
              title="Equity curve"
              description="Server-side equity snapshots from the active runtime session."
            >
              {loading ? (
                <div className="flex min-h-72 items-center justify-center rounded-xl border border-border/80 bg-muted/20">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-foreground" />
                </div>
              ) : equitySeries.length === 0 ? (
                <div className="flex min-h-72 items-center justify-center rounded-xl border border-border/80 bg-muted/20 px-6 text-center">
                  <p className="text-sm text-muted-foreground">
                    Equity snapshots appear here once the runtime starts recording heartbeats.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-border/80 bg-background p-4">
                  <EquityChart data={equitySeries} />
                </div>
              )}
            </DashboardPanel>
          </div>
        </div>

        <div className="space-y-4">
          <DashboardPanel
            eyebrow="Preflight"
            title="Last preflight"
            description="The most recent readiness snapshot recorded by the API process."
            action={<ShieldCheck className="h-4 w-4 text-muted-foreground" />}
          >
            {status?.last_preflight ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={status.last_preflight.ready ? 'default' : 'destructive'}>
                    {status.last_preflight.ready ? 'ready' : 'blocked'}
                  </Badge>
                  <Badge variant="outline">
                    {status.last_preflight.provider}/{status.last_preflight.broker}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatUtcTimestamp(status.last_preflight.checked_at)}
                  </span>
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                  {status.last_preflight.message}
                </p>
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Next allowed actions
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {status.last_preflight.next_allowed_actions.map((action) => (
                      <Badge key={action} variant="outline">
                        {action}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      Blocking reasons
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {status.last_preflight.blocking_reasons.length > 0 ? (
                        status.last_preflight.blocking_reasons.map((reason) => (
                          <Badge key={reason} variant="destructive">
                            {reason}
                          </Badge>
                        ))
                      ) : (
                        <Badge variant="outline">none</Badge>
                      )}
                    </div>
                  </div>
                  <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      Warnings
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {status.last_preflight.warnings.length > 0 ? (
                        status.last_preflight.warnings.map((warning) => (
                          <Badge key={warning} variant="secondary">
                            {warning}
                          </Badge>
                        ))
                      ) : (
                        <Badge variant="outline">none</Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                No preflight has been recorded yet for this API process. Run preflight from the launch console before starting a runtime.
              </p>
            )}
          </DashboardPanel>

          <DashboardPanel
            eyebrow="Incidents"
            title="Latest incident"
            description="The newest warning or error signal surfaced by the runtime or controller."
            action={<Siren className="h-4 w-4 text-muted-foreground" />}
          >
            {latestIncident ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={badgeTone(latestIncident.severity)}>
                    {latestIncident.severity}
                  </Badge>
                  <Badge variant="outline">{latestIncident.event}</Badge>
                </div>
                <p className="text-sm leading-6">{latestIncident.summary}</p>
                <p className="text-xs text-muted-foreground">
                  {formatUtcTimestamp(latestIncident.timestamp)}
                </p>
              </div>
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                No warning or error incident has been captured recently.
              </p>
            )}
          </DashboardPanel>

          <DashboardPanel
            eyebrow="Broker sync"
            title="Reconciliation"
            description="Latest broker balance reconciliation reported by the runtime."
            action={<TimerReset className="h-4 w-4 text-muted-foreground" />}
          >
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Last reconciliation
              </p>
              <p className="mt-2 text-sm font-medium">
                {status?.last_reconciliation_at
                  ? formatUtcTimestamp(status.last_reconciliation_at)
                  : '-'}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                status: {status?.last_reconciliation_status ?? 'not reported'}
              </p>
            </div>
            <p className="text-xs leading-5 text-muted-foreground">
              Skip or failure here usually means broker snapshots were unavailable or the runtime intentionally failed closed.
            </p>
          </DashboardPanel>
        </div>
      </div>

      <DashboardPanel
        eyebrow="Runtime log"
        title="Event timeline"
        description="Recent runtime, risk, and reconciliation events streamed from the API process."
      >
        <EventTimeline
          events={hasActiveRuntime ? eventsQuery.data?.events ?? [] : []}
          loading={hasActiveRuntime ? eventsQuery.isLoading : false}
        />
      </DashboardPanel>
    </div>
  )
}
