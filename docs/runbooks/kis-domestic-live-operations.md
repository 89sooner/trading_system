# KIS Domestic Stock Live Operations Runbook

## Prerequisites

1. KIS Open API credentials configured via environment variables:
   - `TRADING_SYSTEM_KIS_APP_KEY` / `TRADING_SYSTEM_KIS_APP_SECRET`
   - `TRADING_SYSTEM_KIS_CANO` / `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`
2. Optional overrides: `TRADING_SYSTEM_KIS_ENV`, `TRADING_SYSTEM_KIS_BASE_URL`, `TRADING_SYSTEM_KIS_MARKET_DIV`

## Workflow: CSV Backtest -> KIS Preflight -> Guarded Live

### Step 1: CSV Backtest

```bash
TRADING_SYSTEM_CSV_DIR=data/market \
uv run -m trading_system.app.main --mode backtest --provider csv --broker paper --symbols 005930
```

Verify the backtest completes and produces equity/drawdown curves.

### Step 2: KIS Preflight

```bash
TRADING_SYSTEM_KIS_APP_KEY=your-key \
TRADING_SYSTEM_KIS_APP_SECRET=your-secret \
TRADING_SYSTEM_KIS_CANO=12345678 \
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 \
uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930
```

The default `--live-execution preflight` fetches a real-time KIS quote and returns a structured readiness result:
- `ready: true/false`
- `reasons`: list of issues (e.g. `market_closed`, `zero_volume`, `quote_error`)
- `quote_summary`: symbol, price, volume

### Step 3: Guarded Live Execution

```bash
TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true \
TRADING_SYSTEM_LIVE_BAR_SAMPLES=2 \
TRADING_SYSTEM_KIS_APP_KEY=your-key \
TRADING_SYSTEM_KIS_APP_SECRET=your-secret \
TRADING_SYSTEM_KIS_CANO=12345678 \
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 \
uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution live
```

**Guards enforced:**
- `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` must be set
- KRX market hours only (weekdays 09:00-15:30 KST)
- Quote validation (price > 0, volume >= 0)

## Reconciliation

The live loop reconciles the local `PortfolioBook` with KIS broker balance every `TRADING_SYSTEM_RECONCILIATION_INTERVAL` seconds (default: 300).

**Behavior:**
- Cash and position drift is adjusted to match broker snapshot
- Average costs are synced from broker
- Symbols with pending/unresolved orders are skipped (in-transit protection)
- Cash is frozen when any pending order exists
- If the balance query fails, reconciliation is skipped entirely (fail-closed)

**Structured log events:**
- `portfolio.reconciliation.cash_adjusted` — cash drift detected and corrected
- `portfolio.reconciliation.position_adjusted` — position drift detected and corrected
- `portfolio.reconciliation.average_cost_adjusted` — average cost synced from broker
- `portfolio.reconciliation.symbol_skipped` — symbol skipped due to pending order
- `portfolio.reconciliation.cash_frozen` — cash frozen due to pending symbols
- `portfolio.reconciliation.skipped` — entire reconciliation skipped (snapshot unavailable)

## Monitoring via Dashboard

The `/dashboard` UI shows:
- Provider and symbols
- Market session status (open/closed) for KIS provider
- Last reconciliation timestamp and status
- Reconciliation events highlighted in amber in the event feed

## Known Constraints

1. `/api/v1/live/preflight` now supports multiple symbols; legacy consumers may still read `quote_summary`, while newer consumers should prefer `quote_summaries` plus `symbol_count`
2. KIS unresolved-order detection currently depends on broker-reported `ord_psbl_qty` from the balance snapshot; if that signal is unavailable for a held symbol, reconciliation is skipped fail-closed instead of assuming no pending order
3. Reconciliation interval can be declared in YAML as `app.reconciliation_interval`, but `TRADING_SYSTEM_RECONCILIATION_INTERVAL` remains the runtime env override for the live loop
