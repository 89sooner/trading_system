'use client'

import { useQueryClient, useQuery } from '@tanstack/react-query'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { createStrategyProfile } from '@/lib/api/strategies'
import { listPatternSets } from '@/lib/api/patterns'
import { parseMap } from '@/lib/strategyParser'
import { userMessageForError } from '@/lib/api/client'
import { useState } from 'react'

const schema = z.object({
  strategyId: z.string().min(1, 'Required'),
  strategyName: z.string().min(1, 'Required'),
  patternSetId: z.string().min(1, 'Select a pattern set'),
  tradeQuantity: z.string().optional(),
  labelMap: z.string().optional(),
  thresholds: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.tradeQuantity) {
    const n = Number(data.tradeQuantity)
    if (!Number.isFinite(n)) {
      ctx.addIssue({
        code: 'custom',
        message: 'Must be a valid number',
        path: ['tradeQuantity'],
      })
    } else if (n <= 0) {
      ctx.addIssue({
        code: 'custom',
        message: 'Must be positive',
        path: ['tradeQuantity'],
      })
    }
  }
})

type FormValues = z.infer<typeof schema>

export function StrategyForm() {
  const qc = useQueryClient()
  const [serverMessage, setServerMessage] = useState<{ text: string; isError: boolean } | null>(null)

  const { data: patternSets } = useQuery({
    queryKey: ['patterns'],
    queryFn: listPatternSets,
    staleTime: 30_000,
  })

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { patternSetId: '' },
  })

  async function onSubmit(values: FormValues) {
    setServerMessage(null)
    try {
      const created = await createStrategyProfile({
        strategy_id: values.strategyId,
        name: values.strategyName,
        strategy: {
          type: 'pattern_signal',
          pattern_set_id: values.patternSetId,
          label_to_side: parseMap(values.labelMap ?? ''),
          trade_quantity: values.tradeQuantity ? Number(values.tradeQuantity) : null,
          threshold_overrides: parseMap(values.thresholds ?? '', (v) => {
            const n = Number(v)
            if (!Number.isFinite(n)) throw new Error(`Invalid threshold value: "${v}"`)
            return n
          }),
        },
      })
      setServerMessage({ text: `Saved: ${created.strategy_id}`, isError: false })
      await qc.invalidateQueries({ queryKey: ['strategies'] })
      reset()
    } catch (err) {
      setServerMessage({ text: userMessageForError(err), isError: true })
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="space-y-1">
        <Label htmlFor="strategyId">Strategy ID</Label>
        <Input id="strategyId" placeholder="ma-crossover-1" {...register('strategyId')} />
        {errors.strategyId && <p className="text-xs text-danger">{errors.strategyId.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="strategyName">Name</Label>
        <Input id="strategyName" placeholder="MA Crossover" {...register('strategyName')} />
        {errors.strategyName && <p className="text-xs text-danger">{errors.strategyName.message}</p>}
      </div>

      <div className="space-y-1">
        <Label>Pattern Set</Label>
        <Controller
          control={control}
          name="patternSetId"
          render={({ field }) => (
            <Select
              value={field.value}
              onValueChange={(v) => field.onChange(v === null ? '' : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select pattern set" />
              </SelectTrigger>
              <SelectContent>
                {(patternSets ?? []).map((ps) => (
                  <SelectItem key={ps.pattern_set_id} value={ps.pattern_set_id}>
                    {ps.name} ({ps.pattern_set_id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.patternSetId && <p className="text-xs text-danger">{errors.patternSetId.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="tradeQuantity">Trade Quantity</Label>
        <Input id="tradeQuantity" type="number" step="any" placeholder="0.1" {...register('tradeQuantity')} />
        {errors.tradeQuantity && <p className="text-xs text-danger">{errors.tradeQuantity.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="labelMap">Label → Side (key=value per line)</Label>
        <Textarea id="labelMap" rows={3} placeholder={'bullish=buy\nbearish=sell'} {...register('labelMap')} />
      </div>

      <div className="space-y-1">
        <Label htmlFor="thresholds">Threshold Overrides (key=value per line)</Label>
        <Textarea id="thresholds" rows={3} placeholder={'bullish=0.7\nbearish=0.6'} {...register('thresholds')} />
      </div>

      <div className="col-span-full">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : 'Save Strategy Profile'}
        </Button>
      </div>

      {serverMessage && (
        <p className={`col-span-full text-xs ${serverMessage.isError ? 'text-danger' : 'text-success'}`}>
          {serverMessage.text}
        </p>
      )}
    </form>
  )
}
