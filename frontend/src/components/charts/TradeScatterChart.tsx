import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'
import type { Trade } from '@/api/types'
import { formatUtcTimestamp } from '@/lib/formatters'

export function TradeScatterChart({ trades }: { trades: Trade[] }) {
  const data = trades.map((t) => ({ x: Date.parse(t.entry_time), y: Number(t.pnl), symbol: t.symbol }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <ScatterChart>
        <XAxis dataKey="x" type="number" domain={['auto', 'auto']} tickFormatter={(v) => formatUtcTimestamp(new Date(v).toISOString())} tick={{ fill: '#94a3b8', fontSize: 10 }} tickCount={4} name="Entry Time" />
        <YAxis dataKey="y" tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v) => `$${v}`} name="PnL" />
        <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
        <Tooltip
          contentStyle={{ background: '#18212f', border: '1px solid #1e2a3a', color: '#f1f5f9', fontSize: 12 }}
          formatter={(v: number, name: string) => [name === 'y' ? `$${v.toFixed(2)}` : v, name === 'y' ? 'PnL' : 'Entry']}
        />
        <Scatter data={data}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.y >= 0 ? '#22c55e' : '#ef4444'} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  )
}
