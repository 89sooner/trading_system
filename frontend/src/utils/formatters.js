const numberFmt = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const currencyFmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const percentFmt = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateFmt = new Intl.DateTimeFormat("en-US", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "UTC",
});

export function formatDecimal(value) {
  const n = Number(value);
  return Number.isFinite(n) ? numberFmt.format(n) : "-";
}

export function formatCurrency(value) {
  const n = Number(value);
  return Number.isFinite(n) ? currencyFmt.format(n) : "-";
}

export function formatPercentFromRatio(value) {
  const n = Number(value);
  return Number.isFinite(n) ? percentFmt.format(n) : "-";
}

export function formatUtcTimestamp(timestamp) {
  const t = Date.parse(timestamp);
  return Number.isFinite(t) ? dateFmt.format(new Date(t)) : "-";
}
