# Phase 3 Task Breakdown

## Status Note (2026-03-31)

- 이 문서는 Phase 3 시점의 계획/추적 기록이며, 이후 `phase_3_5`, `phase_4`, `phase_5` 문서가 일부 범위를 대체하거나 재정의했다.
- 아래 unchecked 항목은 모두 현재 활성 backlog를 의미하지 않는다.
- 특히 frontend/dashboard 관련 항목과 single-symbol 제약 관련 항목은 이후 phase 문서에서 superseded 또는 re-scoped 되었다.
- 현재 follow-up 추적은 `prd/phase_6_prd.md`를 우선 기준으로 삼는다.

## Epic A - Runtime State And Dashboard
- [x] Define an authoritative runtime state/control object shared by the live loop and API layer
- [x] Refactor live startup so the dashboard reads real loop state, heartbeat, and uptime from that authority
- [x] Expose `GET /api/v1/dashboard/status`
- [x] Expose `GET /api/v1/dashboard/positions`
- [x] Expose `GET /api/v1/dashboard/events`
- [x] Expose `POST /api/v1/dashboard/control` for `pause`, `resume`, and `reset`, with kill switch mapped to pause-only behavior
- [x] Make `reset` valid only for clearing `EMERGENCY` state and returning the runtime to `PAUSED`
- [ ] Ensure control actions are safe against race conditions with the running loop
- [x] Keep an in-memory recent-event buffer in `StructuredLogger`
- [ ] Create or refine `frontend/dashboard.html` to show status, heartbeat, positions, unrealized PnL, and recent events
- [ ] Add navigation entry points from the existing frontend
- [x] Write route and runtime interaction tests for dashboard behavior

## Epic B - Portfolio-Level Risk Defense
- [x] Finalize `PortfolioRiskLimits` around session peak equity using realized plus unrealized portfolio value
- [ ] Add configuration for drawdown guard, SL, TP, and emergency liquidation behavior
- [x] Extend `TradingContext` to carry the portfolio-level risk policy cleanly
- [x] Block new entries when the drawdown limit is breached
- [x] Emit high-severity structured events for drawdown breaches
- [x] Trigger emergency liquidation of open positions when the drawdown limit is breached
- [x] Move the runtime into a guarded risk state after emergency liquidation
- [x] Keep SL and TP execution in the independent risk layer
- [x] Add regression tests for breach, liquidation, guarded-state behavior, and SL/TP edge cases

## Epic C - Unified Multi-Symbol Orchestration
- [x] Update live orchestration to process every configured symbol each cycle
- [x] Maintain per-symbol last-processed timestamps
- [x] Maintain per-symbol strategy instances with isolated state
- [x] Build per-symbol strategy instances once at service startup and reuse them for the full run
- [x] Keep a shared `PortfolioBook` and a single order path through `step.py`
- [x] Implement FIFO allocation in configured symbol order for capital contention
- [ ] Remove live-only single-symbol restrictions that conflict with Phase 3
- [x] Extend backtest orchestration so multi-symbol behavior is testable through the same execution path
- [x] Update strategy factory and related interfaces for per-symbol dispatch where needed
- [x] Write deterministic multi-symbol tests covering cash contention and symbol isolation

## Epic D - Trade Analytics
- [x] Create trade extraction from fill events
- [x] Define the `Trade` or `CompletedTrade` model with entry, exit, quantity, pnl, and holding time
- [x] Implement win rate
- [x] Implement risk-reward ratio
- [x] Implement trade-sequence max drawdown
- [x] Implement average time in market
- [x] Expose trade stats through `GET /api/v1/analytics/backtests/{run_id}/trades` with stable DTOs
- [ ] Add tests for partial fills, scale-in, scale-out, flat-then-reopen, and empty trade sets

## Epic E - Broker Reconciliation
- [x] Add broker account snapshot support to the broker interface
- [x] Implement a reconciliation service that compares broker state with `PortfolioBook`
- [x] Add live-only reconciliation cadence in the live loop with a default of 300 seconds
- [x] Emit structured adjustment events when drift is detected
- [x] Reflect broker-proven external deposits and withdrawals in the local ledger
- [x] Skip symbol adjustments for in-transit orders and freeze all cash adjustments for that reconciliation cycle
- [x] Add reconciliation unit and integration tests

## Cross-Cutting
- [x] Keep `step.py` as the unified execution path for trading behavior changes
- [ ] Update `configs/base.yaml`, `examples/`, `README.md`, and `GEMINI.md` for any config or operator workflow changes
- [ ] Run targeted unit tests after each epic
- [ ] Run broader regression tests after behavior-changing epics
- [x] Run `ruff check src tests`
- [ ] Run the full test suite before declaring Phase 3 complete
