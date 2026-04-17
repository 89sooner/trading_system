'use client'

import { useState, useTransition } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { postLiveRuntimeStart } from '@/lib/api/dashboard'
import { queryClient } from '@/lib/queryClient'
import { userMessageForError } from '@/lib/api/client'

export function RuntimeLaunchForm() {
  const [symbols, setSymbols] = useState('BTCUSDT')
  const [provider, setProvider] = useState<'mock' | 'csv' | 'kis'>('mock')
  const [broker, setBroker] = useState<'paper' | 'kis'>('paper')
  const [liveExecution, setLiveExecution] = useState<'paper' | 'live'>('paper')
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [isPending, startTransition] = useTransition()

  function startRuntime() {
    startTransition(async () => {
      try {
        const payload = {
          symbols: symbols
            .split(',')
            .map((symbol) => symbol.trim().toUpperCase())
            .filter(Boolean),
          provider,
          broker,
          live_execution: liveExecution,
        }
        const data = await postLiveRuntimeStart(payload)
        setMessage({
          text: `Session '${data.session_id}' starting in ${data.live_execution} mode.`,
          isError: false,
        })
        await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      } catch (error) {
        setMessage({ text: userMessageForError(error), isError: true })
      }
    })
  }

  return (
    <div className="space-y-4 rounded-xl border bg-card p-4">
      <div>
        <h2 className="text-sm font-medium">Launch Runtime</h2>
        <p className="text-xs text-muted-foreground">Start a live paper or guarded live session from the dashboard.</p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor="runtime-symbols">Symbols</Label>
          <Input
            id="runtime-symbols"
            value={symbols}
            onChange={(event) => setSymbols(event.target.value)}
            placeholder="BTCUSDT or 005930,035720"
          />
        </div>
        <div className="space-y-1">
          <Label>Execution Mode</Label>
          <Select value={liveExecution} onValueChange={(value) => setLiveExecution(value as 'paper' | 'live')}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="paper">paper</SelectItem>
              <SelectItem value="live">live</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label>Provider</Label>
          <Select value={provider} onValueChange={(value) => setProvider(value as 'mock' | 'csv' | 'kis')}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="mock">mock</SelectItem>
              <SelectItem value="csv">csv</SelectItem>
              <SelectItem value="kis">kis</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label>Broker</Label>
          <Select value={broker} onValueChange={(value) => setBroker(value as 'paper' | 'kis')}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="paper">paper</SelectItem>
              <SelectItem value="kis">kis</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button size="sm" onClick={startRuntime} disabled={isPending || symbols.trim() === ''}>
          {isPending ? 'Starting...' : 'Start Runtime'}
        </Button>
        {message && (
          <p className={`text-xs ${message.isError ? 'text-danger' : 'text-success'}`}>
            {message.text}
          </p>
        )}
      </div>
    </div>
  )
}
