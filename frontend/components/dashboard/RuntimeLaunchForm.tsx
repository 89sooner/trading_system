'use client'

import { useMemo, useState, useTransition } from 'react'
import { AlertTriangle, CheckCircle2, PlayCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DashboardPanel } from '@/components/dashboard/DashboardPanel'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { postLivePreflight, postLiveRuntimeStart } from '@/lib/api/dashboard'
import { userMessageForError } from '@/lib/api/client'
import { formatUtcTimestamp } from '@/lib/formatters'
import { queryClient } from '@/lib/queryClient'
import type { LivePreflightResponseDTO } from '@/lib/api/types'
import { cn } from '@/lib/utils'

type Provider = 'mock' | 'csv' | 'kis'
type Broker = 'paper' | 'kis'
type ExecutionMode = 'paper' | 'live'

const sectionClass = 'rounded-xl border border-border/80 bg-muted/20 p-4'

function toneClass(isError: boolean): string {
  return isError ? 'text-danger' : 'text-success'
}

function statusBadgeClass(status: 'pass' | 'warn' | 'fail'): string {
  if (status === 'pass') return 'bg-success/10 text-success border-success/20'
  if (status === 'warn') return 'bg-warning/12 text-warning border-warning/20'
  return 'bg-danger/10 text-danger border-danger/20'
}

export function RuntimeLaunchForm() {
  const [symbols, setSymbols] = useState('005930')
  const [provider, setProvider] = useState<Provider>('kis')
  const [broker, setBroker] = useState<Broker>('kis')
  const [liveExecution, setLiveExecution] = useState<ExecutionMode>('paper')
  const [tradeQuantity, setTradeQuantity] = useState('1')
  const [maxPosition, setMaxPosition] = useState('1')
  const [maxOrderSize, setMaxOrderSize] = useState('1')
  const [maxNotional, setMaxNotional] = useState('300000')
  const [startingCash, setStartingCash] = useState('300000')
  const [feeBps, setFeeBps] = useState('5')
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [readiness, setReadiness] = useState<LivePreflightResponseDTO | null>(null)
  const [readinessSignature, setReadinessSignature] = useState<string | null>(null)
  const [confirmLiveOpen, setConfirmLiveOpen] = useState(false)
  const [isPending, startTransition] = useTransition()

  const payload = useMemo(
    () => ({
      symbols: symbols
        .split(',')
        .map((symbol) => symbol.trim().toUpperCase())
        .filter(Boolean),
      provider,
      broker,
      live_execution: liveExecution,
      risk: {
        max_position: maxPosition,
        max_notional: maxNotional,
        max_order_size: maxOrderSize,
      },
      backtest: {
        starting_cash: startingCash,
        fee_bps: feeBps,
        trade_quantity: tradeQuantity,
      },
    }),
    [
      broker,
      feeBps,
      liveExecution,
      maxNotional,
      maxOrderSize,
      maxPosition,
      provider,
      startingCash,
      symbols,
      tradeQuantity,
    ],
  )

  const currentSignature = JSON.stringify(payload)
  const readinessIsFresh = readinessSignature === currentSignature
  const selectedActionAllowed =
    readinessIsFresh && readiness?.next_allowed_actions.includes(liveExecution)
  const hasBlockingReasons = (readiness?.blocking_reasons.length ?? 0) > 0
  const liveOrderGateDetails =
    readiness?.checks.find((check) => check.name === 'live_order_gate')?.details ?? null
  const isGuardedLive = liveExecution === 'live'

  function syncExecutionMode(next: ExecutionMode) {
    setLiveExecution(next)
    setMessage(null)
    setReadinessSignature(null)
    if (next === 'live') {
      setProvider('kis')
      setBroker('kis')
      setTradeQuantity('1')
      setMaxPosition('1')
      setMaxOrderSize('1')
    }
  }

  function setAndInvalidate<T>(setter: (value: T) => void, value: T) {
    setter(value)
    setMessage(null)
    setReadinessSignature(null)
  }

  function runPreflight() {
    startTransition(async () => {
      try {
        const response = await postLivePreflight(payload)
        setReadiness(response)
        setReadinessSignature(currentSignature)
        setMessage({
          text: response.ready
            ? `Preflight passed with ${response.warnings.length} warning(s).`
            : `Preflight blocked start: ${response.blocking_reasons.join(', ') || response.message}`,
          isError: !response.ready,
        })
        await queryClient.invalidateQueries({ queryKey: ['dashboard', 'status'] })
      } catch (error) {
        setMessage({ text: userMessageForError(error), isError: true })
      }
    })
  }

  function startRuntime() {
    startTransition(async () => {
      try {
        const data = await postLiveRuntimeStart(payload)
        setMessage({
          text: `Session '${data.session_id}' is starting in ${data.live_execution} mode.`,
          isError: false,
        })
        await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      } catch (error) {
        setMessage({ text: userMessageForError(error), isError: true })
      }
    })
  }

  const canStart =
    payload.symbols.length > 0 &&
    readinessIsFresh &&
    selectedActionAllowed &&
    !hasBlockingReasons &&
    !isPending

  return (
    <>
      <DashboardPanel
        eyebrow="Launch Console"
        title="Start a runtime session"
        description="Use the same operator workflow every time: configure the route, run preflight, review blockers, then launch paper or guarded live."
        action={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{provider}</Badge>
            <Badge variant="outline">{broker}</Badge>
            <Badge variant={liveExecution === 'live' ? 'destructive' : 'secondary'}>
              {liveExecution === 'live' ? 'guarded live' : 'paper'}
            </Badge>
          </div>
        }
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_320px]">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="runtime-symbols">Symbols</Label>
              <Input
                id="runtime-symbols"
                value={symbols}
                onChange={(event) => setAndInvalidate(setSymbols, event.target.value)}
                placeholder="005930 or 005930,035720"
              />
            </div>
            <div className="space-y-1">
              <Label>Execution Mode</Label>
              <Select
                value={liveExecution}
                onValueChange={(value) => syncExecutionMode(value as ExecutionMode)}
              >
                <SelectTrigger aria-label="Execution Mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paper">paper</SelectItem>
                  <SelectItem value="live">live</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Provider</Label>
              <Select
                value={provider}
                onValueChange={(value) => setAndInvalidate(setProvider, value as Provider)}
                disabled={liveExecution === 'live'}
              >
                <SelectTrigger aria-label="Provider">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mock">mock</SelectItem>
                  <SelectItem value="csv">csv</SelectItem>
                  <SelectItem value="kis">kis</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Broker</Label>
              <Select
                value={broker}
                onValueChange={(value) => setAndInvalidate(setBroker, value as Broker)}
                disabled={liveExecution === 'live'}
              >
                <SelectTrigger aria-label="Broker">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paper">paper</SelectItem>
                  <SelectItem value="kis">kis</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="runtime-trade-quantity">Trade Quantity</Label>
              <Input
                id="runtime-trade-quantity"
                type="number"
                min="1"
                step="1"
                value={tradeQuantity}
                disabled={isGuardedLive}
                onChange={(event) => setAndInvalidate(setTradeQuantity, event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="runtime-max-position">Max Position</Label>
              <Input
                id="runtime-max-position"
                type="number"
                min="1"
                step="1"
                value={maxPosition}
                disabled={isGuardedLive}
                onChange={(event) => setAndInvalidate(setMaxPosition, event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="runtime-max-order-size">Max Order Size</Label>
              <Input
                id="runtime-max-order-size"
                type="number"
                min="1"
                step="1"
                value={maxOrderSize}
                disabled={isGuardedLive}
                onChange={(event) => setAndInvalidate(setMaxOrderSize, event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="runtime-max-notional">Max Notional</Label>
              <Input
                id="runtime-max-notional"
                type="number"
                min="1"
                step="10000"
                value={maxNotional}
                onChange={(event) => setAndInvalidate(setMaxNotional, event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="runtime-starting-cash">Starting Cash</Label>
              <Input
                id="runtime-starting-cash"
                type="number"
                min="0"
                step="10000"
                value={startingCash}
                onChange={(event) => setAndInvalidate(setStartingCash, event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="runtime-fee-bps">Fee Bps</Label>
              <Input
                id="runtime-fee-bps"
                type="number"
                min="0"
                step="0.1"
                value={feeBps}
                onChange={(event) => setAndInvalidate(setFeeBps, event.target.value)}
              />
            </div>
          </div>

          <div className={cn(sectionClass, 'space-y-3')}>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Operating policy
              </p>
              <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                <p>Run preflight on the exact route you intend to launch.</p>
                <p>Paper can start when no blocking reason remains.</p>
                <p>Guarded live additionally requires KIS, open market, and live-order opt-in.</p>
              </div>
            </div>
            <div className="border-t border-border/80 pt-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Current request
              </p>
              <p className="mt-2 text-sm font-medium">
                {payload.symbols.length > 0 ? payload.symbols.join(', ') : 'No symbols selected'}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {provider} / {broker} / {liveExecution}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                qty {tradeQuantity} / max position {maxPosition} / max order {maxOrderSize}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                max notional {maxNotional} / starting cash {startingCash} / fee {feeBps} bps
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-border/80 pt-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium">Preflight before launch</p>
            <p className="text-xs text-muted-foreground">
              Start stays disabled until the latest preflight matches the current configuration.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={runPreflight}
              disabled={isPending || payload.symbols.length === 0}
            >
              {isPending ? 'Checking...' : 'Run Preflight'}
            </Button>
            <Button
              size="sm"
              onClick={() =>
                liveExecution === 'live' ? setConfirmLiveOpen(true) : startRuntime()
              }
              disabled={!canStart}
            >
              <PlayCircle className="mr-1.5 h-4 w-4" />
              Start Runtime
            </Button>
          </div>
        </div>

        {message ? <p className={cn('text-sm', toneClass(message.isError))}>{message.text}</p> : null}

        {readiness ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.9fr)]">
            <div className="space-y-4">
              <div className={sectionClass}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={readiness.ready ? 'default' : 'destructive'}>
                    {readiness.ready ? 'Ready to proceed' : 'Blocked'}
                  </Badge>
                  {!readinessIsFresh ? (
                    <Badge variant="secondary">Config changed since the last preflight</Badge>
                  ) : null}
                  {readiness.checked_at ? (
                    <span className="text-xs text-muted-foreground">
                      Checked {formatUtcTimestamp(readiness.checked_at)}
                    </span>
                  ) : null}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{readiness.message}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-border/80 bg-background p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      Blocking reasons
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {readiness.blocking_reasons.length > 0 ? (
                        readiness.blocking_reasons.map((reason) => (
                          <Badge key={reason} variant="destructive">
                            {reason}
                          </Badge>
                        ))
                      ) : (
                        <Badge variant="outline">none</Badge>
                      )}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border/80 bg-background p-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      Warnings
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {readiness.warnings.length > 0 ? (
                        readiness.warnings.map((warning) => (
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

              <div className={sectionClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Readiness checks
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {readiness.checks.map((check) => (
                    <div
                      key={check.name}
                      className="rounded-lg border border-border/80 bg-background p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium">{check.name}</p>
                        <Badge
                          variant="outline"
                          className={statusBadgeClass(check.status)}
                        >
                          {check.status}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs leading-5 text-muted-foreground">
                        {check.summary}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className={cn(sectionClass, 'space-y-4')}>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Allowed next actions
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {readiness.next_allowed_actions.map((action) => (
                    <Badge
                      key={action}
                      variant={action === liveExecution ? 'default' : 'outline'}
                    >
                      {action}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Per-symbol checks
                </p>
                {readiness.symbol_checks.map((check) => (
                  <div
                    key={check.symbol}
                    className="rounded-lg border border-border/80 bg-background p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">{check.symbol}</p>
                      <Badge
                        variant="outline"
                        className={statusBadgeClass(check.status)}
                      >
                        {check.status}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-muted-foreground">
                      {check.summary}
                    </p>
                    {check.price || check.volume ? (
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                        <div className="rounded-md border border-border/80 bg-muted/20 px-2 py-2">
                          <span className="block uppercase tracking-[0.14em]">Price</span>
                          <span className="mt-1 block font-mono text-foreground">
                            {check.price ?? '-'}
                          </span>
                        </div>
                        <div className="rounded-md border border-border/80 bg-muted/20 px-2 py-2">
                          <span className="block uppercase tracking-[0.14em]">Volume</span>
                          <span className="mt-1 block font-mono text-foreground">
                            {check.volume ?? '-'}
                          </span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </DashboardPanel>

      <Dialog open={confirmLiveOpen} onOpenChange={setConfirmLiveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm guarded live launch</DialogTitle>
            <DialogDescription>
              This route can submit real orders through the KIS adapter. Confirm only after reviewing the latest preflight and market status.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-xl border border-danger/25 bg-danger/5 p-4 text-sm text-danger">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                Guarded live remains unavailable unless the latest matching preflight explicitly allows{' '}
                <span className="font-semibold">live</span>.
              </p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <ConfirmField label="Symbols" value={payload.symbols.join(', ') || '-'} />
            <ConfirmField label="Route" value={`${provider} / ${broker} / ${liveExecution}`} />
            <ConfirmField label="Trade Quantity" value={tradeQuantity} />
            <ConfirmField label="Max Order Size" value={maxOrderSize} />
            <ConfirmField label="Max Position" value={maxPosition} />
            <ConfirmField label="Max Notional" value={maxNotional} />
            <ConfirmField
              label="KIS Environment"
              value={liveOrderGateDetails?.kis_env ?? 'unknown'}
            />
            <ConfirmField
              label="Live Orders Flag"
              value={liveOrderGateDetails?.live_orders_enabled ?? 'unknown'}
            />
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" size="sm" />}>
              Cancel
            </DialogClose>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                setConfirmLiveOpen(false)
                startRuntime()
              }}
              disabled={!canStart}
            >
              <CheckCircle2 className="mr-1.5 h-4 w-4" />
              Start guarded live
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function ConfirmField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/80 bg-muted/20 p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 break-words font-mono text-sm text-foreground">{value}</p>
    </div>
  )
}
