# Phase 3 Implementation Plan

## Goal
Implement Phase 3 as a production-hardening layer on top of the Phase 1 and 2 execution foundation. The plan must preserve the unified execution path, add operator visibility and control, protect the portfolio at runtime, support multi-symbol processing with shared capital, expose trade-level analytics from fills, and reconcile local portfolio state against the broker.

## Assumptions
- `src/trading_system/execution/step.py` remains the single trading decision and order path for both backtest and live behavior changes.
- Existing dashboard-related and portfolio-risk-related code can be refactored if it does not fully satisfy the PRD.
- Reconciliation is part of Phase 3 scope, but it should ship after the core runtime and risk foundations are in place because it depends on trustworthy runtime state.
- Multi-symbol capital contention uses FIFO allocation in configured symbol order.
- Multi-symbol strategy execution uses per-symbol strategy instances rather than shared stateful strategy objects.
- Per-symbol strategy instances are built once during service initialization and reused for the full run.
- Trade statistics are exposed through `GET /api/v1/analytics/backtests/{run_id}/trades` rather than only embedded inside existing backtest responses.
- Reconciliation runs in live mode only, defaults to a 300-second cadence, and skips symbol adjustments plus all cash adjustments when any affected order is in transit.

## Impacted Files

### Runtime and orchestration
- `src/trading_system/app/loop.py`
- `src/trading_system/app/state.py`
- `src/trading_system/app/services.py`
- `src/trading_system/execution/step.py`
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/reconciliation.py`

### Risk and portfolio
- `src/trading_system/risk/portfolio_limits.py`
- `src/trading_system/portfolio/book.py`
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`

### API and dashboard
- `src/trading_system/api/server.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/routes/analytics.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/core/ops.py`
- `frontend/dashboard.html`
- `frontend/index.html`

### Strategy and analytics
- `src/trading_system/strategy/factory.py`
- `src/trading_system/strategy/base.py`
- `src/trading_system/analytics/trades.py`
- `src/trading_system/analytics/trade_stats.py`

### Tests and docs
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_portfolio_risk_limits.py`
- `tests/unit/test_live_loop_multi_symbol.py`
- `tests/unit/test_trade_stats.py`
- `tests/unit/test_reconciliation.py`
- `tests/integration/` additions where runtime interaction matters
- `configs/base.yaml`
- `examples/`
- `README.md`
- `GEMINI.md`

## Implementation Steps

1. Establish the authoritative live runtime state for operator control.
Define how the API process and live loop share state before adding more dashboard behavior. This step should make loop state, heartbeat, uptime, and control actions authoritative rather than best-effort references on `app.state`. Introduce a small runtime control object owned by the live process and exposed to the API layer. The operator kill switch maps to pause-only behavior; it does not liquidate positions. The dashboard control API supports `pause`, `resume`, and `reset`, where `reset` is only for leaving an emergency risk state and transitions the runtime back to `PAUSED`.

2. Complete the dashboard around that runtime state.
Expose status, positions, and recent events through API routes and a minimal frontend. The dashboard should show estimated marks and unrealized PnL, and it must surface pause and resume controls. Event streaming can start with polling, but the route contract should be stable enough to support later transport upgrades.

3. Refactor portfolio risk to match the PRD, not only the current partial implementation.
Move drawdown and SL/TP behavior into the risk layer used by `step.py`. Daily drawdown handling must do more than skip evaluation: it must block new entries, emit high-severity events, trigger an emergency portfolio unwind policy, and move the runtime into a guarded state that prevents immediate re-entry. Configuration should include drawdown and SL/TP thresholds plus any emergency unwind settings.

4. Make multi-symbol execution a unified behavior across live and backtest.
Extend orchestration so every configured symbol is processed through the same `step.py` path with independent per-symbol strategy instances and shared portfolio accounting. Build the symbol-to-strategy map once during service initialization and reuse it for the full run in both backtest and live modes. Do not leave backtest on a single-symbol-only path if live behavior changes depend on multi-symbol state. Use FIFO allocation for cash contention in configured symbol order and cover it with deterministic tests.

5. Add trade extraction and PRD-aligned trade statistics.
Create trade objects from fill events with explicit pairing rules for partial fills, scale-ins, and scale-outs. Compute the required metrics first: win rate, risk-reward ratio, trade-sequence max drawdown, and average time in market. Expose them through `GET /api/v1/analytics/backtests/{run_id}/trades` as the initial dedicated analytics API. Live-session analytics can remain follow-up work after the backtest route is stable.

6. Add broker reconciliation as a first-class Phase 3 capability.
Extend the broker interface with an account snapshot method, add a reconciliation service, and run it in the live loop on a default 300-second cadence. Reconciliation must compare broker state to `PortfolioBook`, emit structured adjustment events, skip symbol adjustments for affected in-transit orders, and freeze all cash adjustments for that reconciliation cycle.

7. Update configuration, examples, and operator documentation together.
Any configuration shape changes must be reflected in `configs/`, `examples/`, `README.md`, and `GEMINI.md`. Operator docs should explain dashboard control, emergency risk behavior, multi-symbol constraints, and reconciliation semantics.

## Epic Breakdown

### Epic A. Runtime State And Dashboard
- Introduce an authoritative runtime-control/state object shared by the live loop and API layer.
- Expose status, heartbeat, uptime, open positions, and recent events.
- Implement dashboard `pause`, `resume`, and `reset` control against the authoritative runtime state, with kill switch mapped to pause-only behavior and `reset` returning `EMERGENCY` to `PAUSED`.
- Add frontend dashboard polling UI.

### Epic B. Portfolio-Level Risk Defense
- Finish `PortfolioRiskLimits` so equity uses realized plus unrealized exposure.
- Add emergency drawdown handling with entry blocking, liquidation, and guarded runtime transition.
- Keep SL/TP execution in the risk layer, not strategy code.
- Emit warning or critical events for every guardrail action.

### Epic C. Unified Multi-Symbol Orchestration
- Extend `LiveTradingLoop` and backtest orchestration to process multiple symbols.
- Add per-symbol timestamps and per-symbol strategy instances with isolated history.
- Use FIFO allocation in configured symbol order for capital contention.
- Ensure strategy factory and runtime orchestration materialize per-symbol strategy instances once per run and reuse them for the full run.

### Epic D. Trade Analytics
- Extract completed trades from fills.
- Implement PRD-required metrics only as the initial scope.
- Surface trade stats through `GET /api/v1/analytics/backtests/{run_id}/trades` with stable DTOs.

### Epic E. Broker Reconciliation
- Add broker account snapshot support.
- Implement live-only reconciliation with a default 300-second cadence and drift detection.
- Apply safe local corrections and emit adjustment events, but skip symbol adjustments and freeze all cash adjustments while affected orders are in transit.
- Handle external deposits and withdrawals as first-class reconciliation outcomes.

## Test Plan

### Unit Tests
- Dashboard route tests for status, positions, events, and `pause`/`resume`/`reset` control actions.
- Portfolio risk tests for peak-equity tracking, drawdown breach, liquidation triggers, guarded emergency state transitions, and SL/TP edge cases.
- Multi-symbol loop tests for per-symbol processing, per-symbol strategy isolation, build-once lifecycle, FIFO cash contention, and deterministic ordering.
- Trade extraction tests for partial fills, reopen flows, and average holding time.
- Reconciliation tests for no-op sync, adjustment events, external cash changes, symbol skip, and cash-freeze behavior during in-transit protection.

### Integration Tests
- Live runtime/API integration test proving dashboard control changes loop behavior.
- Multi-symbol simulation test proving the same orchestration logic works in backtest and live scaffolds.
- Reconciliation integration test against broker stubs that model pending and settled orders.

### Manual Verification
- Run the live server and dashboard together, confirm heartbeat updates and operator controls work.
- Force a drawdown breach and verify new entries stop, positions unwind, and the runtime remains guarded.
- Run two or more symbols with constrained cash and verify the allocation policy is observable in logs.
- Simulate broker drift and verify reconciliation emits an adjustment event and updates the local book safely.

## Risks And Follow-Up
- If live runtime control is not authoritative, the dashboard will look correct while not actually controlling the loop.
- If multi-symbol support lands only in live mode, strategy behavior will drift from backtest and become hard to validate.
- If reconciliation ships before in-transit semantics are explicit, it can damage the local book.
- Async provider or broker access may be required once multi-symbol polling is exercised under real latency; treat that as an implementation concern to assess during Epic C and Epic E, not as a speculative refactor upfront.
