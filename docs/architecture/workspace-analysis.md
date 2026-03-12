# Workspace Analysis

This document captures the current implementation state of the trading-system workspace as of March 12, 2026.

## Repository state

The repository is still at scaffold stage. The package layout under `src/trading_system/` matches the intended layered design, but most modules currently define contracts or small value objects rather than full workflows.

Implemented behavior today:

- `risk.limits.RiskLimits` enforces order size, projected position, and projected notional checks.
- `portfolio.book.PortfolioBook` updates cash and positions from fills.
- `analytics.metrics.cumulative_return` computes a simple equity-curve return.
- Unit coverage exists only for `RiskLimits`.

Scaffolded but not orchestrated yet:

- `data.provider.MarketDataProvider` defines the historical/live bar contract.
- `strategy.base.Strategy` and `StrategySignal` define signal generation contracts.
- `execution.orders.OrderRequest` models order intent.
- `backtest.engine.BacktestContext` groups a portfolio, risk limits, and fees but does not execute a backtest loop.

## Layer analysis

### Data

`MarketDataProvider.load_bars()` returns `Iterable[MarketBar]`, which is flexible enough for both backtest and streaming-like adapters. The interface is minimal and clean, but it does not yet capture timeframe, range selection, or multi-symbol loading. Those omissions are reasonable for a scaffold, but they will matter as soon as the backtest engine is implemented.

### Strategy

The strategy layer exposes a single-bar `evaluate(bar)` contract and returns a `StrategySignal` with side, quantity, and reason. This keeps hidden state out of the interface, but it also means any stateful strategy will need explicit internal state management or a richer context object. That design decision should be made before adding a real strategy implementation.

### Risk

`RiskLimits.allows_order()` is the only domain rule with tests and real decision logic. It currently uses projected position notional as the notional check. That is internally consistent, but it assumes a single-symbol perspective and does not distinguish between gross exposure, net exposure, or per-order notional. Future risk work should keep those concepts explicit to avoid backtest/live drift.

### Execution

The execution layer stops at `OrderRequest`. There is no broker protocol, no order-to-fill lifecycle, and no mapping from `StrategySignal` to `OrderRequest`. This is the main missing boundary between intent generation and state mutation.

### Portfolio

`PortfolioBook.apply_fill()` correctly moves signed quantity into positions and adjusts cash by `signed_quantity * fill_price`. The model is intentionally small, but it currently has no fee handling, average price tracking, realized/unrealized PnL, or zero-position cleanup. Those gaps are acceptable at this stage, but they limit analytics and backtest realism.

### Backtest

`BacktestContext` exists only as a container. There is no orchestration loop joining data, strategy, risk, execution, portfolio, and analytics into a deterministic simulation. This is the largest functional gap in the workspace.

### Analytics

`cumulative_return()` provides one safe, deterministic metric with edge-case handling for empty curves and zero starting equity. No drawdown, trade statistics, turnover, or fee-aware performance metrics exist yet.

## Current flow and missing links

The intended flow is visible from the package boundaries:

1. `MarketDataProvider` yields `MarketBar`.
2. `Strategy.evaluate()` produces `StrategySignal`.
3. Risk checks determine whether the desired quantity is allowed.
4. Execution should convert the signal into `OrderRequest`.
5. Portfolio should update from fills.
6. Analytics should consume the resulting equity curve.

The missing links are:

- No adapter converts `StrategySignal` into `OrderRequest`.
- No broker or fill model exists between execution and portfolio.
- No backtest loop coordinates iteration, state transitions, and fee application.
- No portfolio-to-analytics bridge produces an equity curve.

## Config and example consistency

The configuration surface is only partially aligned.

- `config/settings.py` defines `RiskSettings` and `BacktestSettings`, but there is no loader or top-level application settings model.
- `configs/base.yaml` contains `app` and `market_data` sections that are not represented in typed settings.
- `examples/sample_backtest.yaml` contains strategy metadata and a `risk.max_order_size`, but omits `risk.max_notional`, which is required by `RiskLimits`.
- The example file therefore describes a scenario that cannot yet be materialized into the current typed models without extra defaults or translation logic.

Before implementing config loading, the repository should decide whether examples are intentionally aspirational or expected to be executable fixtures.

## Test coverage assessment

Current test coverage is narrow and focused on one happy path and one rejection case for `RiskLimits`.

Highest-priority missing tests:

1. Risk boundary cases for projected position and projected notional.
2. Portfolio regression tests covering buys, sells, sign handling, and flatting a position.
3. Analytics tests for empty, single-point, zero-start, and positive/negative return curves.
4. Contract-level tests for strategy and execution adapters once those components exist.
5. A minimal integration test for the future backtest loop.

## Recommended next backlog

### 1. Add a deterministic backtest loop

Implement a small engine that iterates bars, calls a strategy, enforces `RiskLimits`, applies fills to `PortfolioBook`, and records an equity curve. Keep all time progression driven by input bars.

### 2. Introduce execution and fill contracts

Add explicit broker or simulator interfaces plus a fill model so the transition from desired action to portfolio mutation is not implicit.

### 3. Normalize configuration models

Create a typed top-level settings model and align `configs/base.yaml`, `examples/sample_backtest.yaml`, and the settings dataclasses so example configs can be loaded without hidden defaults.

### 4. Expand foundational tests

Add unit tests around portfolio behavior and analytics, then add one integration-style backtest smoke test to lock the orchestration path before strategy complexity grows.
