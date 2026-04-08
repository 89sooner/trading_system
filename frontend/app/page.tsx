'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { createBacktestRun } from '@/lib/api/backtests'
import { listStrategyProfiles } from '@/lib/api/strategies'
import { useRunsStore } from '@/store/runsStore'
import { userMessageForError } from '@/lib/api/client'

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
        description="Configure and launch a backtest or live preflight run"
      />

      <Card>
        <CardHeader><CardTitle>Run Configuration</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="symbol">Symbol</Label>
              <Input id="symbol" placeholder="BTCUSDT" {...register('symbol')} />
              {errors.symbol && <p className="text-xs text-danger">{errors.symbol.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Strategy Profile</Label>
              <Controller
                control={control}
                name="strategyProfileId"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={(v) => field.onChange(v ?? '')}>
                    <SelectTrigger><SelectValue placeholder="Select strategy" /></SelectTrigger>
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
            <div className="space-y-1">
              <Label htmlFor="maxPosition">Max Position</Label>
              <Input id="maxPosition" type="number" step="any" {...register('maxPosition', { valueAsNumber: true })} />
              {errors.maxPosition && <p className="text-xs text-danger">{errors.maxPosition.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="maxNotional">Max Notional</Label>
              <Input id="maxNotional" type="number" {...register('maxNotional', { valueAsNumber: true })} />
              {errors.maxNotional && <p className="text-xs text-danger">{errors.maxNotional.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="maxOrderSize">Max Order Size</Label>
              <Input id="maxOrderSize" type="number" step="any" {...register('maxOrderSize', { valueAsNumber: true })} />
              {errors.maxOrderSize && <p className="text-xs text-danger">{errors.maxOrderSize.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="startingCash">Starting Cash</Label>
              <Input id="startingCash" type="number" {...register('startingCash', { valueAsNumber: true })} />
              {errors.startingCash && <p className="text-xs text-danger">{errors.startingCash.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="tradeQuantity">Trade Quantity</Label>
              <Input id="tradeQuantity" type="number" step="any" {...register('tradeQuantity', { valueAsNumber: true })} />
              {errors.tradeQuantity && <p className="text-xs text-danger">{errors.tradeQuantity.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="feeBps">Fee (bps)</Label>
              <Input id="feeBps" type="number" {...register('feeBps', { valueAsNumber: true })} />
              {errors.feeBps && <p className="text-xs text-danger">{errors.feeBps.message}</p>}
            </div>
            <div className="col-span-full">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Running...' : 'Start Backtest'}
              </Button>
            </div>
            {serverError && <p className="col-span-full text-xs text-danger">{serverError}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
