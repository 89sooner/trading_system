# KIS Domestic Stock Live Operations Runbook

## Prerequisites

1. KIS Open API credentials configured via environment variables:
   - `TRADING_SYSTEM_KIS_APP_KEY` / `TRADING_SYSTEM_KIS_APP_SECRET`
   - `TRADING_SYSTEM_KIS_CANO` / `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`
2. Optional overrides: `TRADING_SYSTEM_KIS_ENV`, `TRADING_SYSTEM_KIS_BASE_URL`, `TRADING_SYSTEM_KIS_MARKET_DIV`
3. If you plan to use the dashboard/API path, also configure `TRADING_SYSTEM_ALLOWED_API_KEYS`.

## Recommended environment template

Use a local `.env` or shell export set equivalent to the following.
Keep `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=false` until the final guarded-live step.

```dotenv
TRADING_SYSTEM_ENV=local
TRADING_SYSTEM_TIMEZONE=Asia/Seoul

TRADING_SYSTEM_KIS_APP_KEY=your-kis-app-key
TRADING_SYSTEM_KIS_APP_SECRET=your-kis-app-secret
TRADING_SYSTEM_KIS_CANO=12345678
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01

TRADING_SYSTEM_KIS_ENV=prod
TRADING_SYSTEM_KIS_MARKET_DIV=J
# TRADING_SYSTEM_KIS_BASE_URL=
# TRADING_SYSTEM_KIS_PRICE_TR_ID=
# TRADING_SYSTEM_KIS_BALANCE_TR_ID=

TRADING_SYSTEM_ENABLE_LIVE_ORDERS=false
TRADING_SYSTEM_LIVE_BAR_SAMPLES=2
TRADING_SYSTEM_LIVE_POLL_INTERVAL=10
TRADING_SYSTEM_HEARTBEAT_INTERVAL=60
TRADING_SYSTEM_RECONCILIATION_INTERVAL=300

TRADING_SYSTEM_ALLOWED_API_KEYS=your-strong-api-key
# DATABASE_URL=postgresql://...
```

## Supported launch paths

There are now two supported ways to operate KIS live trading:

1. CLI path
   - `--mode live --provider kis --broker kis --live-execution preflight|paper|live`
2. API/dashboard path
   - `POST /api/v1/live/runtime/start`
   - Dashboard launch form on `/dashboard`

The same KIS guards still apply in both paths:
- `provider=kis`, `broker=kis`
- `live_execution=live` only when `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`
- KRX market hours only for real order submission
- Quote validation and preflight must succeed

## Workflow: CSV Backtest -> KIS Preflight -> Paper Rehearsal -> Guarded Live

### Step 1: CSV Backtest

```bash
TRADING_SYSTEM_CSV_DIR=data/market uv run -m trading_system.app.main --mode backtest --provider csv --broker paper --symbols 005930
```

Verify the backtest completes and produces equity/drawdown curves.

### Step 2: KIS Preflight

```bash
TRADING_SYSTEM_KIS_APP_KEY=your-key TRADING_SYSTEM_KIS_APP_SECRET=your-secret TRADING_SYSTEM_KIS_CANO=12345678 TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930
```

The default `--live-execution preflight` fetches a real-time KIS quote and returns a structured readiness result:
- `ready: true/false`
- `reasons`: list of issues (e.g. `market_closed`, `zero_volume`, `quote_error`)
- `quote_summary`: symbol, price, volume

### Step 3: Paper rehearsal

CLI example:

```bash
TRADING_SYSTEM_KIS_APP_KEY=your-key TRADING_SYSTEM_KIS_APP_SECRET=your-secret TRADING_SYSTEM_KIS_CANO=12345678 TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution paper
```

API/dashboard example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/live/runtime/start   -H "Content-Type: application/json"   -H "X-API-Key: your-strong-api-key"   -d '{"mode":"live","symbols":["005930"],"provider":"kis","broker":"kis","live_execution":"paper"}'
```

Use this rehearsal to verify the runtime session can be started, monitored, paused, resumed, and stopped without submitting real orders.

### Step 4: Guarded live execution

```bash
TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true TRADING_SYSTEM_LIVE_BAR_SAMPLES=2 TRADING_SYSTEM_KIS_APP_KEY=your-key TRADING_SYSTEM_KIS_APP_SECRET=your-secret TRADING_SYSTEM_KIS_CANO=12345678 TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution live
```

**Guards enforced:**
- `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` must be set
- KRX market hours only (weekdays 09:00-15:30 KST)
- Quote validation (price > 0, volume >= 0)

## Readiness checklist before any KIS live session

- [ ] KIS app key/secret, account number, and product code are all present in the current shell or `.env`
- [ ] `provider=kis` and `broker=kis` are explicitly selected
- [ ] One tradable symbol is chosen first; do not start with a multi-symbol live order session
- [ ] `TRADING_SYSTEM_ENABLE_LIVE_ORDERS` is still `false` during preflight and paper rehearsal
- [ ] `preflight` returns `ready=true` with no unresolved `reasons`
- [ ] Dashboard/API auth path is confirmed if you plan to operate through `/dashboard`
- [ ] Stop procedure is known before the session starts (`POST /api/v1/dashboard/control` with `stop` or dashboard Stop button)

## Paper rehearsal checklist

Run at least one full paper session before enabling real order submission.

- [ ] Start a paper session for one symbol only
- [ ] Confirm dashboard status shows a non-empty `session_id`
- [ ] Confirm `controller_state=active` and loop `state=running`
- [ ] Confirm `last_heartbeat` advances without long gaps
- [ ] Confirm `positions`, `events`, and `equity` endpoints return live data while the session is active
- [ ] Confirm reconciliation events are reasonable and not permanently stuck on `portfolio.reconciliation.skipped`
- [ ] Confirm `portfolio.reconciliation.pending_source` is emitted and uses `open_orders` when KIS provides that source
- [ ] Export session order audit records through `/api/v1/order-audit/export?scope=live_session&owner_id=<session_id>&format=csv`
- [ ] Review completed session evidence through `/dashboard/sessions` or `/api/v1/live/runtime/sessions/<session_id>/evidence`
- [ ] Confirm `pause` changes state to `paused`
- [ ] Confirm `resume` changes state back to `running`
- [ ] Confirm `stop` returns the dashboard to a clean disconnected/stopped state
- [ ] Repeat the same paper launch/stop cycle at least twice without orphaned session state

## First real-order checklist

Only after the paper rehearsal is stable:

- [ ] Confirm KRX market is open right now
- [ ] Keep to a single symbol and minimum trade quantity
- [ ] Re-run preflight immediately before switching `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`
- [ ] Verify dashboard is already reachable and the stop path is ready
- [ ] Monitor `system.control`, `system.heartbeat`, `system.error`, `order.*`, and `portfolio.reconciliation.*` events during the first run
- [ ] If anything is unclear, stop and return to paper mode instead of continuing in live mode

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
- `portfolio.reconciliation.pending_source` — pending-order authority used for the reconciliation attempt (`open_orders`, `balance_snapshot`, `unavailable`)

## Monitoring via Dashboard

The `/dashboard` UI shows:
- Provider and symbols
- Market session status (open/closed) for KIS provider
- Controller state, active session id, and last runtime error when no loop is active
- Last reconciliation timestamp and status
- Reconciliation events highlighted in amber in the event feed

## Known Constraints

1. `/api/v1/live/preflight` now supports multiple symbols; legacy consumers may still read `quote_summary`, while newer consumers should prefer `quote_summaries` plus `symbol_count`
2. KIS unresolved-order detection currently depends on broker-reported `ord_psbl_qty` from the balance snapshot; if that signal is unavailable for a held symbol, reconciliation is skipped fail-closed instead of assuming no pending order
3. Reconciliation interval can be declared in YAML as `app.reconciliation_interval`, but `TRADING_SYSTEM_RECONCILIATION_INTERVAL` remains the runtime env override for the live loop
4. There is still no durable order lifecycle store; treat the first real KIS session as a supervised rollout, not a hands-off production run
