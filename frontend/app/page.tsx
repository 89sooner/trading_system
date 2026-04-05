'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
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

export default function CreateRunPage() {
  const router = useRouter()
  const { saveRun } = useRunsStore()
  const [strategyProfileId, setStrategyProfileId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isPending, setIsPending] = useState(false)

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: listStrategyProfiles,
    staleTime: 30_000,
  })

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    setError(null)
    setIsPending(true)
    try {
      const symbol = String(fd.get('symbol')).trim().toUpperCase()
      const result = await createBacktestRun({
        mode: 'backtest',
        symbols: [symbol],
        risk: {
          max_position: Number(fd.get('maxPosition')),
          max_notional: Number(fd.get('maxNotional')),
          max_order_size: Number(fd.get('maxOrderSize')),
        },
        backtest: {
          starting_cash: Number(fd.get('startingCash')),
          fee_bps: Number(fd.get('feeBps')),
          trade_quantity: Number(fd.get('tradeQuantity')),
        },
        strategy: {
          type: 'pattern_signal',
          profile_id: strategyProfileId || null,
        },
      })

      saveRun({
        runId: result.run_id,
        status: result.status,
        symbol,
        strategyProfile: strategyProfileId || null,
        createdAt: new Date().toISOString(),
      })

      router.push(`/runs/${result.run_id}`)
    } catch (err) {
      setError(userMessageForError(err))
    } finally {
      setIsPending(false)
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
          <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="symbol">Symbol</Label>
              <Input id="symbol" name="symbol" required placeholder="BTCUSDT" />
            </div>
            <div className="space-y-1">
              <Label>Strategy Profile</Label>
              <Select value={strategyProfileId} onValueChange={(v) => setStrategyProfileId(v ?? '')}>
                <SelectTrigger><SelectValue placeholder="Select strategy" /></SelectTrigger>
                <SelectContent>
                  {(strategies ?? []).map((s) => (
                    <SelectItem key={s.strategy_id} value={s.strategy_id}>
                      {s.name} ({s.strategy_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="maxPosition">Max Position</Label>
              <Input id="maxPosition" name="maxPosition" type="number" step="any" defaultValue="1.0" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="maxNotional">Max Notional</Label>
              <Input id="maxNotional" name="maxNotional" type="number" defaultValue="100000" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="maxOrderSize">Max Order Size</Label>
              <Input id="maxOrderSize" name="maxOrderSize" type="number" step="any" defaultValue="0.25" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="startingCash">Starting Cash</Label>
              <Input id="startingCash" name="startingCash" type="number" defaultValue="100000" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="tradeQuantity">Trade Quantity</Label>
              <Input id="tradeQuantity" name="tradeQuantity" type="number" step="any" defaultValue="0.1" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="feeBps">Fee (bps)</Label>
              <Input id="feeBps" name="feeBps" type="number" defaultValue="5" />
            </div>
            <div className="col-span-full">
              <Button type="submit" disabled={isPending}>
                {isPending ? 'Running...' : 'Start Backtest'}
              </Button>
            </div>
            {error && <p className="col-span-full text-xs text-danger">{error}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
