import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useFormStatus } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { createBacktestRun } from '@/api/backtests'
import { listStrategyProfiles } from '@/api/strategies'
import { useRunsStore } from '@/store/runsStore'
import { userMessageForError } from '@/api/client'

export const Route = createFileRoute('/')({
  component: CreateRunPage,
})

function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <Button type="submit" disabled={pending}>
      {pending ? 'Running...' : 'Start Backtest'}
    </Button>
  )
}

function CreateRunPage() {
  const navigate = useNavigate()
  const { saveRun } = useRunsStore()
  const [strategyProfileId, setStrategyProfileId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: listStrategyProfiles,
    staleTime: 30_000,
  })

  async function formAction(fd: FormData) {
    setError(null)
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
          profile_id: String(fd.get('strategyProfileId') || '') || null,
        },
      })

      saveRun({
        runId: result.run_id,
        status: result.status,
        symbol,
        strategyProfile: strategyProfileId || null,
        createdAt: new Date().toISOString(),
      })

      navigate({ to: '/runs/$runId', params: { runId: result.run_id } })
    } catch (err) {
      setError(userMessageForError(err))
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">New Backtest Run</h1>
      <Card>
        <CardHeader><CardTitle>Run Configuration</CardTitle></CardHeader>
        <CardContent>
          <form action={formAction} className="grid grid-cols-2 gap-3">
            <input type="hidden" name="strategyProfileId" value={strategyProfileId} />
            <div className="space-y-1">
              <Label htmlFor="symbol">Symbol</Label>
              <Input id="symbol" name="symbol" required placeholder="BTCUSDT" />
            </div>
            <div className="space-y-1">
              <Label>Strategy Profile</Label>
              <Select value={strategyProfileId} onValueChange={setStrategyProfileId}>
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
            <div className="col-span-2">
              <SubmitButton />
            </div>
            {error && <p className="col-span-2 text-xs text-red-400">{error}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
