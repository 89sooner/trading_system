import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { EquityPoint } from '@/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function EquityCurveChart({ data }: { data: EquityPoint[] }) {
  const chartData = data.map((d) => ({ t: Date.parse(d.timestamp), v: Number(d.equity) }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="t" type="number" domain={['auto', 'auto']} tickFormatter={(v) => formatUtcTimestamp(new Date(v).toISOString())} tick={{ fill: '#94a3b8', fontSize: 10 }} tickCount={4} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
        <Tooltip
          contentStyle={{ background: '#18212f', border: '1px solid #1e2a3a', color: '#f1f5f9', fontSize: 12 }}
          formatter={(v: number) => [`$${v.toFixed(2)}`, 'Equity']}
          labelFormatter={(l) => formatUtcTimestamp(new Date(l).toISOString())}
        />
        <Area type="monotone" dataKey="v" stroke="#3b82f6" fill="url(#equityGrad)" strokeWidth={1.5} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
