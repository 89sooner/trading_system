'use client'

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { DrawdownPoint } from '@/lib/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function DrawdownChart({ data }: { data: DrawdownPoint[] }) {
  const chartData = data.map((d) => ({ t: Date.parse(d.timestamp), v: Number(d.drawdown) }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="oklch(0.65 0.2 25)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="oklch(0.65 0.2 25)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="t" type="number" domain={['auto', 'auto']} tickFormatter={(v) => formatUtcTimestamp(new Date(v).toISOString())} tick={{ fill: 'oklch(0.55 0 0)', fontSize: 10 }} tickCount={4} />
        <YAxis tick={{ fill: 'oklch(0.55 0 0)', fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ background: 'oklch(0.2 0.02 260)', border: '1px solid oklch(0.3 0.02 260)', color: 'oklch(0.9 0 0)', fontSize: 12 }}
          formatter={(v) => [`${Number(v).toFixed(2)}%`, 'Drawdown']}
          labelFormatter={(l) => formatUtcTimestamp(new Date(l).toISOString())}
        />
        <Area type="monotone" dataKey="v" stroke="oklch(0.65 0.2 25)" fill="url(#drawdownGrad)" strokeWidth={1.5} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
