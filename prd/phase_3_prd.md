# Product Requirements Document (PRD) - Phase 3

## 1. Overview
Phase 1 and Phase 2 established the unified execution path, portfolio persistence, and a continuously running live loop. Phase 3 extends that base into a production-oriented operating system for trading by adding:

- live observability and operator control
- portfolio-level defensive risk controls
- multi-symbol execution on the same engine instance
- trade-level analytics built from actual fills
- broker/exchange reconciliation to keep the local ledger trustworthy

The goal is not to add new alpha sources. The goal is to make the existing system safer, more observable, and operable across multiple symbols under real runtime constraints.

## 2. Product Goals

### Goal 1. Live Observability
Operators must be able to inspect the state of the live system without relying only on terminal logs.

### Goal 2. Portfolio Protection
Risk protection must operate above the individual order level and be able to halt or unwind the portfolio when configured limits are breached.

### Goal 3. Multi-Symbol Operation
One trading engine instance must process multiple symbols while preserving a single execution path and shared portfolio accounting.

### Goal 4. Trustworthy Portfolio State
The local `PortfolioBook` must be continuously reconcilable against broker-reported balances and positions.

### Goal 5. Actionable Analytics
Trade analytics must be expressed in trade units derived from actual fills, not only in bar-level or portfolio-level summaries.

## 3. Detailed Requirements

### 3.1 Real-Time Live Dashboard
- Show the backend loop state and last heartbeat in a web UI.
- Show active positions with symbol, quantity, average cost, estimated mark, and unrealized PnL.
- Stream or poll recent events such as orders, fills, rejections, reconciliation adjustments, and runtime errors.
- Provide an operator control surface to pause trading, resume trading, and reset an emergency risk state.
- Expose a kill-switch action that pauses trading without requiring shell access. This operator action does not liquidate positions; emergency liquidation is reserved for risk-triggered flows.
- The dashboard control API is the single operator control surface for runtime state transitions. `resume` only clears a normal paused state. `reset` clears an emergency risk state and returns the runtime to `PAUSED`, after which an operator may explicitly resume trading.

### 3.2 Advanced Risk And Analytics
- Enforce a portfolio daily drawdown limit based on realized plus unrealized PnL relative to the session peak equity.
- When the daily drawdown limit is breached:
  - block new entries
  - emit a high-severity risk event
  - transition runtime to an explicit emergency risk state that requires a manual operator reset before trading can resume
  - liquidate open positions according to an explicit emergency exit policy
- Support dynamic stop-loss and take-profit checks in an independent risk layer rather than strategy-specific code.
- Build `Trade` objects from fill events that represent complete entry-to-exit cycles.
- Expose initial trade analytics through `GET /api/v1/analytics/backtests/{run_id}/trades`.
- Compute and expose, at minimum:
  - win rate
  - risk-reward ratio
  - max drawdown at the trade-stat level or trade sequence level
  - average time in market

### 3.3 Multi-Symbol Orchestration
- Process every configured symbol in each live loop cycle.
- Maintain independent per-symbol strategy instances, indicator history, and last-processed timestamps.
- Build per-symbol strategy instances once at service startup and reuse them for the full run in both backtest and live modes.
- Preserve a single shared `PortfolioBook` and a single order/risk path through `step.py`.
- Use FIFO allocation when multiple symbols compete for limited cash or buying power. Symbols are evaluated in configured processing order, and earlier eligible orders consume available capital first.
- Keep behavior deterministic in backtests so multi-symbol orchestration can be validated outside live mode.

### 3.4 Exchange Reconciliation
- Poll broker balances and positions on a configurable cadence. The default production cadence is every 300 seconds in live mode only.
- Detect drift between broker-reported state and the local `PortfolioBook`.
- Emit structured adjustment events when corrections are applied.
- Reflect external cash movements such as deposits and withdrawals when the broker state proves they occurred.
- Skip automatic adjustments for symbols affected by in-transit orders, and freeze all cash adjustments for that reconciliation cycle, so reconciliation does not overwrite legitimate pending activity.

## 4. Non-Functional Requirements
- Preserve the unified execution path across backtest and live wherever behavior changes affect trading logic.
- Keep strategy, risk, execution, analytics, and portfolio layers separated by explicit interfaces.
- Prefer iterative rollout by epic, but the Phase 3 plan must still cover all five product areas above.
- For multi-symbol live operation, assess whether provider and broker I/O needs asynchronous execution or bounded concurrency.
- Emit high-severity structured events for drawdown breaches, emergency liquidation, and reconciliation adjustments.

## 5. Scope

### In Scope
- backend changes for dashboard support, risk, orchestration, analytics, and reconciliation
- minimal frontend required to operate and monitor the live runtime
- configuration and documentation updates needed to run the new behavior
- tests that prove trading behavior and operator workflows

### Out Of Scope
- new machine-learning models
- new strategy families unrelated to Phase 3 operability
- new third-party exchange ecosystems beyond the current broker/provider surface unless strictly required for reconciliation support

## 6. Success Criteria
- An operator can view runtime status, positions, and recent events from a browser.
- A configured drawdown breach prevents new entries and produces a verified emergency unwind path.
- A single runtime can process multiple symbols while sharing portfolio cash and preserving deterministic backtest coverage.
- Trade statistics are available from completed fills and include the required minimum metrics.
- Broker reconciliation detects and records ledger drift without corrupting in-transit order handling.

## 7. Risks And Assumptions

### Assumptions
- Broker APIs permit balance and position polling at a cadence that is safe for production use.
- The current event logging and persistence infrastructure from Phase 1 and 2 is stable enough to extend rather than replace.

### Risks
- Reconciliation can be wrong if in-transit orders are treated as settled.
- Multi-symbol order contention can cause cash oversubscription without a clear allocation policy.
- Dashboard control can be misleading if the UI and live loop do not share a truly authoritative runtime state.
- Trade extraction can be incorrect around partial fills, scale-ins, and scale-outs unless fill pairing rules are explicit.
