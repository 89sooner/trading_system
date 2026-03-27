const numberFmt = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const currencyFmt = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const percentFmt = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const dateFmt = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'short',
  timeStyle: 'short',
  timeZone: 'UTC',
})

export function formatDecimal(value: unknown): string {
  const n = Number(value)
  return Number.isFinite(n) ? numberFmt.format(n) : '-'
}

export function formatCurrency(value: unknown): string {
  const n = Number(value)
  return Number.isFinite(n) ? currencyFmt.format(n) : '-'
}

export function formatPercentFromRatio(value: unknown): string {
  const n = Number(value)
  return Number.isFinite(n) ? percentFmt.format(n) : '-'
}

export function formatUtcTimestamp(timestamp: unknown): string {
  const t = Date.parse(String(timestamp))
  return Number.isFinite(t) ? dateFmt.format(new Date(t)) : '-'
}

export function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null) return '–'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h}h ${m}m ${s}s`
}
