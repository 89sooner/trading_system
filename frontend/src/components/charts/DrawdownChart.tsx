import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { DrawdownPoint } from '@/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function DrawdownChart({ data }: { data: DrawdownPoint[] }) {
  const chartData = data.map((d) => ({ t: Date.parse(d.timestamp), v: Number(d.drawdown) }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="t" type="number" domain={['auto', 'auto']} tickFormatter={(v) => formatUtcTimestamp(new Date(v).toISOString())} tick={{ fill: '#94a3b8', fontSize: 10 }} tickCount={4} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ background: '#18212f', border: '1px solid #1e2a3a', color: '#f1f5f9', fontSize: 12 }}
          formatter={(v: number) => [`${v.toFixed(2)}%`, 'Drawdown']}
          labelFormatter={(l) => formatUtcTimestamp(new Date(l).toISOString())}
        />
        <Area type="monotone" dataKey="v" stroke="#ef4444" fill="url(#drawdownGrad)" strokeWidth={1.5} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
