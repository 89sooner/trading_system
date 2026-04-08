'use client'

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { formatUtcTimestamp } from '@/lib/formatters'

export interface EquityDataPoint {
  time: number
  value: number
}

interface EquityChartProps {
  data: EquityDataPoint[]
}

export function EquityChart({ data }: EquityChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="dashEquityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="oklch(0.65 0.15 160)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="oklch(0.65 0.15 160)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="time"
          type="number"
          domain={['auto', 'auto']}
          tickFormatter={(v) => formatUtcTimestamp(new Date(v).toISOString())}
          tick={{ fill: 'oklch(0.55 0 0)', fontSize: 10 }}
          tickCount={4}
        />
        <YAxis
          tick={{ fill: 'oklch(0.55 0 0)', fontSize: 10 }}
          tickFormatter={(v) => `$${Number(v).toLocaleString()}`}
        />
        <Tooltip
          contentStyle={{
            background: 'oklch(0.2 0.02 260)',
            border: '1px solid oklch(0.3 0.02 260)',
            color: 'oklch(0.9 0 0)',
            fontSize: 12,
          }}
          formatter={(v) => [`$${Number(v).toLocaleString()}`, 'Portfolio']}
          labelFormatter={(l) => formatUtcTimestamp(new Date(l).toISOString())}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="oklch(0.65 0.15 160)"
          fill="url(#dashEquityGrad)"
          strokeWidth={1.5}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
