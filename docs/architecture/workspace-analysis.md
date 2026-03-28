# Workspace Analysis

This document captures the current implementation state of the trading-system workspace as of March 28, 2026.

## Repository state

The repository is well beyond a scaffold. It now includes deterministic backtesting, guarded live execution paths, a FastAPI surface, a React frontend, pattern/strategy repositories, trade analytics, dashboard control, portfolio persistence, and KIS integration.

Implemented behavior today:

- `app.main` supports `backtest`, `live` preflight, `live` paper execution, and explicitly gated `live` order submission.
- `app.services` composes strategy repositories, pattern repositories, data providers, broker adapters, risk controls, portfolio persistence, and live preflight checks.
- `execution.step.execute_trading_step` is the shared execution core across backtest and live runtime paths.
- `backtest.engine.run_backtest` orchestrates deterministic replay, event capture, equity tracking, and multi-symbol processing.
- `api.server` exposes backtests, live preflight, patterns, strategies, analytics, and dashboard routes behind API key, CORS, and rate-limit middleware.
- `frontend/src/routes` provides browser workflows for pattern management, strategy profiles, run review, and live dashboard monitoring.
- `execution.reconciliation.reconcile` can align a local `PortfolioBook` with broker snapshots when the broker supports balance snapshots.

## Layer analysis

### App

The app layer cleanly separates CLI argument handling (`app.main`) from service wiring (`app.services`) and runtime control (`app.loop`).

- `--mode backtest` executes the deterministic replay path.
- `--mode live` defaults to preflight, can run a paper loop, and can submit live orders only behind explicit KIS-specific guards.
- `LiveTradingLoop` manages state transitions, heartbeats, reconciliation attempts, and restart-safe portfolio persistence.
- The dashboard API depends on an attached live loop (`create_app(live_loop=...)`) rather than starting the loop itself.

Current limitation:
- There is no built-in frontend or API workflow that starts and owns the live loop process end-to-end.

### Data

The data layer includes three concrete providers:

- `InMemoryMarketDataProvider` for deterministic tests and smoke scenarios
- `CsvMarketDataProvider` with resilience policies for file-backed replay
- `KisQuoteMarketDataProvider` for live quote sampling via KIS

Current limitation:
- The KIS path is quote-sampling based and does not yet provide a richer historical/live market-data adapter surface.

### Strategy

The strategy layer now supports both example and repository-backed flows:

- `MomentumStrategy` remains the default deterministic example strategy
- `PatternSignalStrategy` evaluates learned patterns against incoming windows
- `strategy.factory` resolves inline strategy settings or saved strategy profiles backed by `configs/strategies`

Current limitation:
- There is still no general strategy plugin registry or direct CLI flag set for selecting saved strategy profiles.

### Risk

Risk enforcement operates at both order and portfolio scopes:

- `RiskLimits` enforces max position, max notional, and max order size
- `PortfolioRiskLimits` adds optional session drawdown protection and long-position SL/TP handling
- Emergency drawdown breaches can force liquidation of the active symbol and move runtime state into `EMERGENCY`

Current limitation:
- Portfolio-level policy remains intentionally simple; there is no gross/net exposure model or richer short-specific risk framework.

### Execution

Execution now has explicit, reusable boundaries:

- signal-to-order adapter
- policy-based simulator with fill, slippage, and commission policies
- resilient broker wrapper with retry, timeout, and circuit-breaker behavior
- KIS broker adapter for explicit live-order submission
- reconciliation helper for broker balance snapshots

Current limitation:
- There is no durable order lifecycle store, and the current KIS adapter does not yet expose account balance snapshots for exchange-level reconciliation.

### Portfolio

`PortfolioBook` now supports:

- cash and position updates
- average cost tracking
- realized and unrealized PnL
- fee accumulation
- JSON persistence and reload via `FilePortfolioRepository`

Current limitation:
- Portfolio persistence is snapshot based; there is no event-sourced history, snapshot versioning, or external audit trail.

### Backtest

Backtest orchestration is deterministic and uses the same trading-step core as live execution.

- Bars are merged and ordered across symbols
- Signals, order lifecycle events, and risk rejections are serialized
- The API stores completed runs for later fetch and analytics inspection

Current limitation:
- Backtest runs are executed synchronously and stored only in the in-memory API repository, so results do not survive API process restarts.

### Analytics

Analytics is no longer limited to cumulative return only.

- Backtest result DTOs now expose summary, equity curve, and drawdown curve
- `/api/v1/analytics/backtests/{run_id}/trades` exposes trade extraction and trade-level summary statistics
- The frontend renders summary tiles, drawdown/equity charts, and trade tables from these DTOs

Current limitation:
- There is no persisted analytics store or broader exposure/turnover/benchmark reporting layer yet.

### API and frontend

The operator-facing application surface now exists in addition to the CLI.

- The API covers runtime, patterns, strategies, analytics, and dashboard control
- The frontend provides routes for new runs, saved runs, pattern sets, strategy profiles, and dashboard inspection
- Dashboard control officially supports `pause`, `resume`, and `reset`

Current limitation:
- `/api/v1/live/preflight` still enforces exactly one symbol per request even though the runtime loop and backtest engine can process multiple symbols.

## Configuration and examples

Configuration is currently split between two layers:

- `config.settings.load_settings` validates the baseline YAML schema used for environment, symbols, execution broker, risk, backtest fields, and API CORS settings
- `app.settings.AppSettings` and API request DTOs validate runtime-only fields such as `live_execution`, strategy configuration, and `portfolio_risk`

Examples and operator artifacts include:

- `configs/base.yaml` for baseline typed YAML loading
- `configs/patterns/*.json` and `configs/strategies/*.json` for repository-backed pattern and strategy assets
- `examples/sample_backtest.yaml`, `examples/sample_backtest_krx.yaml`, and `examples/sample_live_kis.yaml` for operator reference

Notes:

- The commented `portfolio_risk` block in `configs/base.yaml` is a reference example only; `config.settings.load_settings` does not currently parse it.
- Strategy/profile and pattern-set storage is file backed, not database backed.

## Test coverage snapshot

Coverage now spans the current operator-facing surface, not only the backtest core.

- Unit tests: config loading, app wiring, dashboard routes, live loop behavior, KIS integration, portfolio risk, reconciliation, repositories, analytics, and execution adapters
- Integration tests: backtest run API, pattern/strategy API flow, trade analytics API, config loader failures, and API security/validation

This gives a strong regression baseline for deterministic replay, runtime validation, dashboard control, and repository-backed pattern/strategy workflows.

## Remaining gaps before broader production use

1. **Durable run storage**: backtest results and run metadata need persistent storage and, ideally, asynchronous job handling.
2. **Frontend live orchestration**: there is no first-class UI flow to start, attach, and manage the live loop process lifecycle.
3. **Config parity**: runtime fields such as `portfolio_risk` and strategy selection are not yet fully represented in the typed YAML loader.
4. **Exchange snapshot integration**: generic reconciliation exists, but KIS account-balance snapshot support is still missing.
5. **Operational hardening**: richer auth, alerting, audit export, and deployment guidance are still lighter than a fully managed trading platform would require.

## Recommended next backlog

1. Add a persistent backtest run repository and asynchronous run execution model.
2. Extend broker integrations, especially KIS, to expose account balance snapshots for reconciliation.
3. Decide whether `portfolio_risk` and strategy runtime settings should become first-class YAML fields or remain API/runtime-only inputs.
4. Add deployment/operator documentation for starting the API server, live loop, and dashboard together.
