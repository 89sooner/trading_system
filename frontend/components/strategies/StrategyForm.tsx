'use client'

import { useState } from 'react'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { createStrategyProfile } from '@/lib/api/strategies'
import { listPatternSets } from '@/lib/api/patterns'
import { parseMap } from '@/lib/strategyParser'
import { userMessageForError } from '@/lib/api/client'

export function StrategyForm() {
  const qc = useQueryClient()
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [patternSetId, setPatternSetId] = useState('')

  const { data: patternSets } = useQuery({
    queryKey: ['patterns'],
    queryFn: listPatternSets,
    staleTime: 30_000,
  })

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const tradeQtyStr = String(fd.get('strategyTradeQuantity')).trim()
    try {
      const created = await createStrategyProfile({
        strategy_id: String(fd.get('strategyId')).trim(),
        name: String(fd.get('strategyName')).trim(),
        strategy: {
          type: 'pattern_signal',
          pattern_set_id: patternSetId,
          label_to_side: parseMap(String(fd.get('strategyLabelMap'))),
          trade_quantity: tradeQtyStr ? Number(tradeQtyStr) : null,
          threshold_overrides: parseMap(String(fd.get('strategyThresholds')), Number),
        },
      })
      setMessage({ text: `Saved: ${created.strategy_id}`, isError: false })
      await qc.invalidateQueries({ queryKey: ['strategies'] })
    } catch (err) {
      setMessage({ text: userMessageForError(err), isError: true })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="space-y-1">
        <Label htmlFor="strategyId">Strategy ID</Label>
        <Input id="strategyId" name="strategyId" required placeholder="ma-crossover-1" />
      </div>
      <div className="space-y-1">
        <Label htmlFor="strategyName">Name</Label>
        <Input id="strategyName" name="strategyName" required placeholder="MA Crossover" />
      </div>
      <div className="space-y-1">
        <Label>Pattern Set</Label>
        <Select value={patternSetId} onValueChange={(v) => setPatternSetId(v ?? '')}>
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
      </div>
      <div className="space-y-1">
        <Label htmlFor="strategyTradeQuantity">Trade Quantity</Label>
        <Input id="strategyTradeQuantity" name="strategyTradeQuantity" type="number" step="any" placeholder="0.1" />
      </div>
      <div className="space-y-1">
        <Label htmlFor="strategyLabelMap">Label → Side (key=value per line)</Label>
        <Textarea id="strategyLabelMap" name="strategyLabelMap" rows={3} placeholder={'bullish=buy\nbearish=sell'} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="strategyThresholds">Threshold Overrides (key=value per line)</Label>
        <Textarea id="strategyThresholds" name="strategyThresholds" rows={3} placeholder={'bullish=0.7\nbearish=0.6'} />
      </div>
      <div className="col-span-full">
        <Button type="submit">Save Strategy Profile</Button>
      </div>
      {message && (
        <p className={`col-span-full text-xs ${message.isError ? 'text-danger' : 'text-success'}`}>
          {message.text}
        </p>
      )}
    </form>
  )
}
