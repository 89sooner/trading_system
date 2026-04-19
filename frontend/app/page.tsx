'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import { useWatch } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Activity, ArrowRight, FlaskConical, ShieldCheck } from 'lucide-react'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { createBacktestRun } from '@/lib/api/backtests'
import { userMessageForError } from '@/lib/api/client'
import { formatCurrency } from '@/lib/formatters'
import { listStrategyProfiles } from '@/lib/api/strategies'
import { useRunsStore } from '@/store/runsStore'

const positiveNumber = z.number().finite().positive()

const schema = z.object({
  symbol: z.string().min(1, 'Required'),
  strategyProfileId: z.string().optional(),
  maxPosition: positiveNumber,
  maxNotional: positiveNumber,
  maxOrderSize: positiveNumber,
  startingCash: positiveNumber,
  feeBps: z.number().finite().nonnegative(),
  tradeQuantity: positiveNumber,
})

type FormValues = z.infer<typeof schema>

const sectionClass = 'rounded-xl border border-border/80 bg-muted/20 p-4'

export default function CreateRunPage() {
  const router = useRouter()
  const { saveRun } = useRunsStore()
  const [serverError, setServerError] = useState<string | null>(null)

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: listStrategyProfiles,
    staleTime: 30_000,
  })

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      symbol: '',
      strategyProfileId: '',
      maxPosition: 1.0,
      maxNotional: 100000,
      maxOrderSize: 0.25,
      startingCash: 100000,
      feeBps: 5,
      tradeQuantity: 0.1,
    },
  })

  const [startingCash, tradeQuantity, feeBps] = useWatch({
    control,
    name: ['startingCash', 'tradeQuantity', 'feeBps'],
  })

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      const symbol = values.symbol.trim().toUpperCase()
      const result = await createBacktestRun({
        mode: 'backtest',
        symbols: [symbol],
        risk: {
          max_position: values.maxPosition,
          max_notional: values.maxNotional,
          max_order_size: values.maxOrderSize,
        },
        backtest: {
          starting_cash: values.startingCash,
          fee_bps: values.feeBps,
          trade_quantity: values.tradeQuantity,
        },
        strategy: {
          type: 'pattern_signal',
          profile_id: values.strategyProfileId || null,
        },
      })

      saveRun({
        runId: result.run_id,
        status: result.status,
        symbol,
        strategyProfile: values.strategyProfileId || null,
        createdAt: new Date().toISOString(),
      })

      router.push(`/runs/${result.run_id}`)
    } catch (err) {
      setServerError(userMessageForError(err))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Backtest Run"
        description="Configure a deterministic run, choose the strategy profile, and launch the workflow that feeds the rest of the operator console."
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Deterministic replay</Badge>
            <Badge variant="outline">Single-symbol launch</Badge>
            <Badge variant="outline">Server-side run history</Badge>
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.95fr)]">
        <SurfacePanel
          eyebrow="Run Setup"
          title="Configure the run"
          description="These inputs define the initial cash, sizing constraints, and strategy route used for the next backtest."
          action={<FlaskConical className="h-4 w-4 text-muted-foreground" />}
        >
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className={sectionClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Instrument and strategy
                </p>
                <div className="mt-4 grid gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="symbol">Symbol</Label>
                    <Input id="symbol" placeholder="BTCUSDT" {...register('symbol')} />
                    {errors.symbol ? (
                      <p className="text-xs text-danger">{errors.symbol.message}</p>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <Label>Strategy Profile</Label>
                    <Controller
                      control={control}
                      name="strategyProfileId"
                      render={({ field }) => (
                        <Select
                          value={field.value}
                          onValueChange={(v) => field.onChange(v ?? '')}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select strategy" />
                          </SelectTrigger>
                          <SelectContent>
                            {(strategies ?? []).map((s) => (
                              <SelectItem key={s.strategy_id} value={s.strategy_id}>
                                {s.name} ({s.strategy_id})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>
                </div>
              </div>

              <div className={sectionClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Portfolio baseline
                </p>
                <div className="mt-4 grid gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="startingCash">Starting Cash</Label>
                    <Input
                      id="startingCash"
                      type="number"
                      {...register('startingCash', { valueAsNumber: true })}
                    />
                    {errors.startingCash ? (
                      <p className="text-xs text-danger">{errors.startingCash.message}</p>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="feeBps">Fee (bps)</Label>
                    <Input
                      id="feeBps"
                      type="number"
                      {...register('feeBps', { valueAsNumber: true })}
                    />
                    {errors.feeBps ? (
                      <p className="text-xs text-danger">{errors.feeBps.message}</p>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="tradeQuantity">Trade Quantity</Label>
                    <Input
                      id="tradeQuantity"
                      type="number"
                      step="any"
                      {...register('tradeQuantity', { valueAsNumber: true })}
                    />
                    {errors.tradeQuantity ? (
                      <p className="text-xs text-danger">{errors.tradeQuantity.message}</p>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>

            <div className={sectionClass}>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Risk guardrails
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="space-y-1">
                  <Label htmlFor="maxPosition">Max Position</Label>
                  <Input
                    id="maxPosition"
                    type="number"
                    step="any"
                    {...register('maxPosition', { valueAsNumber: true })}
                  />
                  {errors.maxPosition ? (
                    <p className="text-xs text-danger">{errors.maxPosition.message}</p>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="maxNotional">Max Notional</Label>
                  <Input
                    id="maxNotional"
                    type="number"
                    {...register('maxNotional', { valueAsNumber: true })}
                  />
                  {errors.maxNotional ? (
                    <p className="text-xs text-danger">{errors.maxNotional.message}</p>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="maxOrderSize">Max Order Size</Label>
                  <Input
                    id="maxOrderSize"
                    type="number"
                    step="any"
                    {...register('maxOrderSize', { valueAsNumber: true })}
                  />
                  {errors.maxOrderSize ? (
                    <p className="text-xs text-danger">{errors.maxOrderSize.message}</p>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-border/80 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <p className="text-sm font-medium">Launch the next run</p>
                <p className="text-xs text-muted-foreground">
                  Backtests are queued on the API and then promoted into run history.
                </p>
              </div>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Running...' : 'Start Backtest'}
                <ArrowRight className="ml-1.5 h-4 w-4" />
              </Button>
            </div>

            {serverError ? <p className="text-sm text-danger">{serverError}</p> : null}
          </form>
        </SurfacePanel>

        <div className="space-y-4">
          <SurfacePanel
            eyebrow="Run Summary"
            title="Current assumptions"
            description="Quick read on the values that most affect the next run."
            action={<Activity className="h-4 w-4 text-muted-foreground" />}
          >
            <div className="grid gap-3">
              <div className={sectionClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Starting cash
                </p>
                <p className="mt-2 text-lg font-semibold">
                  {formatCurrency(startingCash)}
                </p>
              </div>
              <div className={sectionClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Trade quantity
                </p>
                <p className="mt-2 font-mono text-lg font-semibold">
                  {Number.isFinite(Number(tradeQuantity)) ? tradeQuantity : '-'}
                </p>
              </div>
              <div className={sectionClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Fee setting
                </p>
                <p className="mt-2 font-mono text-lg font-semibold">
                  {Number.isFinite(Number(feeBps)) ? `${feeBps} bps` : '-'}
                </p>
              </div>
            </div>
          </SurfacePanel>

          <SurfacePanel
            eyebrow="Operator Notes"
            title="Before you launch"
            description="Use the same rhythm as the dashboard: define, run, review, then promote."
            action={<ShieldCheck className="h-4 w-4 text-muted-foreground" />}
          >
            <div className="space-y-3 text-sm text-muted-foreground">
              <div className={sectionClass}>
                Start from a saved strategy profile when the run is meant to be compared or promoted later.
              </div>
              <div className={sectionClass}>
                Keep notional and order-size limits conservative. The same settings shape flows into the live runtime path.
              </div>
              <div className={sectionClass}>
                After launch, use <span className="font-medium text-foreground">Runs</span> to inspect the result and <span className="font-medium text-foreground">Dashboard</span> for live preflight and runtime operations.
              </div>
            </div>
          </SurfacePanel>
        </div>
      </div>
    </div>
  )
}
