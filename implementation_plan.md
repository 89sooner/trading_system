# Phase 3 Implementation Plan

## Overview
Build on the stabilized Phase 1 & 2 foundations ([step.py](file:///home/roqkf/trading_system/src/trading_system/execution/step.py), [LiveTradingLoop](file:///home/roqkf/trading_system/src/trading_system/app/loop.py#25-120), [FilePortfolioRepository](file:///home/roqkf/trading_system/src/trading_system/portfolio/repository.py#18-56)) to add:
- A real-time live dashboard (API + frontend)
- Portfolio-level drawdown and SL/TP risk guards
- Multi-symbol orchestration in the live loop
- Trade-level analytics (profit factor, Sharpe, etc.)
- Exchange reconciliation integration

> [!IMPORTANT]
> Phase 3 is split into 4 independent epics (A–D). Each epic ships as a standalone PR so regression surface is small. Epic A (dashboard) and Epic B (portfolio risk) are the highest priority.

---

## Epic A — Live Dashboard API + Frontend

### Backend

#### [NEW] `src/trading_system/api/routes/dashboard.py`
- `GET /api/v1/dashboard/status` → returns the current [AppRunnerState](file:///home/roqkf/trading_system/src/trading_system/app/state.py#4-9), last heartbeat timestamp, uptime
- `GET /api/v1/dashboard/positions` → returns all open positions from [PortfolioBook](file:///home/roqkf/trading_system/src/trading_system/portfolio/book.py#7-103) (symbol, qty, avg_cost, unrealized_pnl using last known mark)
- `GET /api/v1/dashboard/events` → paginated last-N log events (pulled from an in-memory ring buffer wired into `StructuredLogger`)
- `POST /api/v1/dashboard/control` → body `{"action": "pause" | "resume" | "stop"}` → mutates [AppRunnerState](file:///home/roqkf/trading_system/src/trading_system/app/state.py#4-9) in the running [LiveTradingLoop](file:///home/roqkf/trading_system/src/trading_system/app/loop.py#25-120)

> [!NOTE]
> The loop state must be shared between the FastAPI process and the loop worker. The approach is: store [LiveTradingLoop](file:///home/roqkf/trading_system/src/trading_system/app/loop.py#25-120) instance on the FastAPI `app.state` at server startup. Dashboard routes read/mutate it through a dependency.

#### [MODIFY] [src/trading_system/api/server.py](file:///home/roqkf/trading_system/src/trading_system/api/server.py)
- Register the new `dashboard_router`
- Accept an optional [LiveTradingLoop](file:///home/roqkf/trading_system/src/trading_system/app/loop.py#25-120) argument in [create_app()](file:///home/roqkf/trading_system/src/trading_system/api/server.py#14-63) and store it on `app.state`

#### [MODIFY] [src/trading_system/api/schemas.py](file:///home/roqkf/trading_system/src/trading_system/api/schemas.py)
- Add `DashboardStatusDTO`, `PositionDTO`, `PositionsResponseDTO`, `ControlActionDTO`, `EventDTO`

#### [MODIFY] [src/trading_system/core/ops.py](file:///home/roqkf/trading_system/src/trading_system/core/ops.py)
- Add an in-memory ring buffer (capped deque, e.g. 500 entries) to `StructuredLogger`
- Expose `.recent_events(limit=50)` method

### Frontend

#### [NEW] `frontend/dashboard.html`
- Status card (state badge, heartbeat timestamp)
- Positions table (symbol / qty / avg_cost / unrealised PnL)
- Event feed (auto-refreshing every 5s via `fetch`)
- Kill switch button (calls `/api/v1/dashboard/control`)

#### [MODIFY] [frontend/index.html](file:///home/roqkf/trading_system/frontend/index.html) + `frontend/src/pages/` nav
- Add nav link to `dashboard.html`

### Tests
- Unit: `tests/unit/test_dashboard_routes.py` — mock `app.state.loop`, verify route contracts
- Smoke: control action changes state, positions reflect `PortfolioBook` contents

---

## Epic B — Portfolio-Level Risk Guards

### Backend

#### [NEW] `src/trading_system/risk/portfolio_limits.py`
```python
@dataclass(slots=True)
class PortfolioRiskLimits:
    max_daily_drawdown_pct: Decimal   # e.g. Decimal("0.05") = 5%
    session_peak_equity: Decimal      # set to starting equity at boot
    sl_pct: Decimal | None = None     # per-position stop-loss %
    tp_pct: Decimal | None = None     # per-position take-profit %

    def is_daily_limit_breached(self, current_equity: Decimal) -> bool: ...
    def sl_triggered(self, symbol: str, avg_cost: Decimal, mark: Decimal, qty: Decimal) -> bool: ...
    def tp_triggered(self, symbol: str, avg_cost: Decimal, mark: Decimal, qty: Decimal) -> bool: ...
```

#### [MODIFY] `src/trading_system/execution/step.py`
- Accept an optional `portfolio_risk: PortfolioRiskLimits | None` on `TradingContext`
- Before calling `strategy.evaluate(bar)`, check `is_daily_limit_breached`. If breached, emit `risk.daily_limit_breached` at WARNING severity and skip the step.
- After `RiskLimits.allows_order` check, evaluate SL/TP on existing positions and auto-generate close orders as needed.

#### [MODIFY] `src/trading_system/app/services.py`
- Wire `PortfolioRiskLimits` (from settings) into `TradingContext` inside `run_live_paper`

#### [MODIFY] `src/trading_system/config/settings.py` + `src/trading_system/app/settings.py`
- Add `PortfolioRiskSettings` dataclass: `max_daily_drawdown_pct`, `sl_pct`, `tp_pct`

#### [MODIFY] `configs/base.yaml` + `examples/` + `README.md`
- Document new settings keys

### Tests
- `tests/unit/test_portfolio_risk_limits.py` — drawdown breach, SL/TP trigger edge cases
- Regression: step skips trading when daily limit breached

---

## Epic C — Multi-Symbol Orchestration

### Backend

#### [MODIFY] `src/trading_system/app/loop.py` — `_run_tick`
- Replace `symbol = self.services.symbols[0]` with a loop over `self.services.symbols`
- Maintain per-symbol `_last_processed_timestamp` as a `dict[str, datetime]`
- Portfolio remains shared; cash allocation is FIFO (first signal to check cash wins)

#### [MODIFY] `src/trading_system/app/services.py` — `_single_symbol` guard
- Remove the guard from `run_live_paper` (was only safety for old scaffold); keep for `run` (backtest) where multi-symbol orchestration is not in scope for Phase 3

#### [MODIFY] `src/trading_system/strategy/factory.py`
- Make `build_strategy` return either a single strategy (applied to all symbols) or a `dict[str, Strategy]` keyed by symbol, depending on settings

### Tests
- `tests/unit/test_live_loop_multi_symbol.py` — mock provider returning stubs for 2 symbols, assert both are processed each tick, portfolio cash is shared

---

## Epic D — Trade-Level Analytics

#### [NEW] `src/trading_system/analytics/trades.py`
```python
@dataclass(frozen=True, slots=True)
class CompletedTrade:
    symbol: str
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    entry_time: datetime
    exit_time: datetime

def extract_trades(fill_events: Sequence[OrderFilledEvent]) -> list[CompletedTrade]: ...
```
- Parses fill event log to match buys against sells (FIFO pairing)

#### [NEW] `src/trading_system/analytics/advanced_metrics.py`
```python
def profit_factor(trades: Sequence[CompletedTrade]) -> Decimal: ...
def average_win(trades: Sequence[CompletedTrade]) -> Decimal: ...
def average_loss(trades: Sequence[CompletedTrade]) -> Decimal: ...
def sharpe_ratio(trades: Sequence[CompletedTrade], risk_free_rate: Decimal = ZERO) -> Decimal: ...
def sortino_ratio(trades: Sequence[CompletedTrade], risk_free_rate: Decimal = ZERO) -> Decimal: ...
```

#### [MODIFY] `src/trading_system/api/routes/backtest.py`
- Enrich `BacktestResultDTO` with `TradeStatsDTO` (profit_factor, avg_win, avg_loss, sharpe, sortino) computed from `fill_events`

### Tests
- `tests/unit/test_trades.py` — FIFO pairing, partial close, flat then reopen
- `tests/unit/test_advanced_metrics.py` — profit_factor edge cases, empty trades → zero return

---

## Epic E — Exchange Reconciliation (Optional Phase 3.5)

> [!WARNING]
> This epic has higher implementation risk (KIS in-transit edge cases). Treat as Phase 3.5 — plan now, ship separately after A–D are merged.

#### [NEW] `src/trading_system/execution/reconciliation.py`
```python
@dataclass(slots=True)
class ReconciliationResult:
    adjusted_cash: Decimal
    adjusted_positions: dict[str, Decimal]
    adjustments_made: list[str]   # human-readable diff log

def reconcile(book: PortfolioBook, broker: BrokerSimulator, logger: StructuredLogger) -> ReconciliationResult: ...
```
- Calls `broker.get_account_balance()` (new method on broker interface) to fetch real cash + positions
- Computes diff vs `PortfolioBook`, emits `portfolio.reconciliation` event at WARNING if diff > threshold
- Applies correction to `PortfolioBook` fields directly

#### [MODIFY] `src/trading_system/execution/broker.py` — `BrokerSimulator` protocol
- Add optional `get_account_balance() -> AccountBalanceSnapshot` method; KIS adapter implements it, simulator stubs it

#### [MODIFY] `src/trading_system/app/loop.py`
- Add a `reconciliation_interval` (default: 300s = every 5 minutes)
- Call `reconcile()` before each tick cycle when interval has passed

---

## Validation Plan

### Automated Tests
```bash
# Run all tests after each epic
uv run --python .venv/bin/python --no-sync pytest -m smoke
uv run --python .venv/bin/python --no-sync pytest

# Lint
uv run --python .venv/bin/python --no-sync ruff check src tests
```

### Manual Verification
- Start server with `uvicorn`, open `dashboard.html`, verify heartbeat updates and position table reflects a running loop
- Set `max_daily_drawdown_pct: 0.01` and force equity below threshold; verify `risk.daily_limit_breached` appears in logs and no new orders emit
- Configure 2 symbols in `--symbols`, verify both are processed in each tick cycle via logs

### PR Strategy
| Epic | Branch | Dependencies |
|------|--------|-------------|
| A — Dashboard | `feature/live-dashboard` | none |
| B — Portfolio Risk | `feature/portfolio-risk` | none |
| C — Multi-symbol | `feature/multi-symbol` | none |
| D — Trade Analytics | `feature/trade-analytics` | none |
| E — Reconciliation | `feature/reconciliation` | C (multi-symbol loop) |
