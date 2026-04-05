'use client'

import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import type { Trade } from '@/lib/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function TradeScatterChart({ trades }: { trades: Trade[] }) {
  const data = trades.map((t) => ({ x: Date.parse(t.entry_time), y: Number(t.pnl), symbol: t.symbol }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <ScatterChart>
        <XAxis dataKey="x" type="number" domain={['auto', 'auto']} tickFormatter={(v) => formatUtcTimestamp(new Date(v).toISOString())} tick={{ fill: 'oklch(0.55 0 0)', fontSize: 10 }} tickCount={4} name="Entry Time" />
        <YAxis dataKey="y" tick={{ fill: 'oklch(0.55 0 0)', fontSize: 10 }} tickFormatter={(v) => `$${v}`} name="PnL" />
        <ReferenceLine y={0} stroke="oklch(0.4 0 0)" strokeDasharray="3 3" />
        <Tooltip
          contentStyle={{ background: 'oklch(0.2 0.02 260)', border: '1px solid oklch(0.3 0.02 260)', color: 'oklch(0.9 0 0)', fontSize: 12 }}
          formatter={(v, name) => [name === 'y' ? `$${Number(v).toFixed(2)}` : v, name === 'y' ? 'PnL' : 'Entry']}
        />
        <Scatter data={data} fill="oklch(0.65 0.15 250)" />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
