# Workspace Analysis

This document captures the current implementation state of the trading-system workspace as of April 19, 2026.

## Repository state

The repository is well beyond a scaffold. It now includes deterministic backtesting, guarded live execution paths, a FastAPI surface, a React frontend, Supabase-backed persistence options, trade analytics, dashboard control, API key administration with governance fields, webhook delivery, portfolio persistence, run metadata, live runtime session history, and KIS integration.

Implemented behavior today:

- `app.main` supports `backtest`, `live` preflight, `live` paper execution, and explicitly gated `live` order submission.
- `app.services` composes strategy repositories, pattern repositories, data providers, broker adapters, risk controls, portfolio persistence, and live preflight checks.
- `execution.step.execute_trading_step` is the shared execution core across backtest and live runtime paths.
- `backtest.engine.run_backtest` orchestrates deterministic replay, event capture, equity tracking, and multi-symbol processing.
- `api.server` exposes backtests, dispatcher status, retention preview/prune, order audit, live preflight, live runtime session history, patterns, strategies, analytics, admin key management, `/health`, and dashboard routes behind API key, CORS, and rate-limit middleware.
- `frontend/app/*` provides browser workflows for backtest submission, pattern management, strategy profiles, run review, API key administration, live dashboard monitoring, and recent live session browsing, now with server-sourced run metadata shown in the review surface.
- `execution.reconciliation.reconcile` can align a local `PortfolioBook` with broker snapshots when the broker supports balance snapshots.
- `notifications.webhook` provides bounded fire-and-forget delivery for selected runtime events through `httpx`.

## Layer analysis

### App

The app layer cleanly separates CLI argument handling (`app.main`) from service wiring (`app.services`) and runtime control (`app.loop`).

- `--mode backtest` executes the deterministic replay path.
- `--mode live` defaults to preflight, can run a paper loop, and can submit live orders only behind explicit KIS-specific guards.
- `LiveTradingLoop` manages state transitions, heartbeats, reconciliation attempts, and restart-safe portfolio persistence.
- The dashboard API can now start and own one live loop process through `LiveRuntimeController`, while also persisting a durable session history.

Current limitation:
- Recent live session history is visible in the dashboard, but long-term search, filtering, and export are not yet implemented.

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
- Order creation, fill, rejection, and risk-rejection events can be stored as durable order audit records, but KIS reconciliation still depends on balance-snapshot pending-order signals rather than a dedicated unresolved-order API.

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
- The API stores completed runs for later fetch and analytics inspection, together with provider/broker/strategy/source metadata.

Current limitation:
- Backtest runs are executed by an API-owned dispatcher with `queued` and `running` states; persistence and metadata are durable through file storage or Supabase. There is still no external queue service or distributed worker model.

### Analytics

Analytics is no longer limited to cumulative return only.

- Backtest result DTOs now expose summary, equity curve, and drawdown curve
- `/api/v1/analytics/backtests/{run_id}/trades` exposes trade extraction and trade-level summary statistics
- The frontend renders summary tiles, drawdown/equity charts, and trade tables from these DTOs

Current limitation:
- There is no persisted analytics store or broader exposure/turnover/benchmark reporting layer yet.

### API and frontend

The operator-facing application surface now exists in addition to the CLI.

- The API covers runtime, live runtime session history, patterns, strategies, analytics, and dashboard control
- The frontend provides routes for new runs, saved runs, pattern sets, strategy profiles, API key administration, and dashboard inspection, with a shared surface design and richer run/admin metadata display
- Dashboard control officially supports `pause`, `resume`, `reset`, and `stop`
- The dashboard consumes SSE (`/api/v1/dashboard/stream`) with polling fallback and server-side equity history (`/api/v1/dashboard/equity`)

Current limitation:
- `/api/v1/live/preflight` now accepts multiple symbols and richer readiness fields, but legacy consumers may still assume a single `quote_summary` field instead of `quote_summaries`/`symbol_count`.

## Configuration and examples

Configuration is currently split between two layers:

- `config.settings.load_settings` validates the baseline YAML schema used for environment, symbols, execution broker, risk, optional `portfolio_risk`, backtest fields, and API CORS settings
- `app.settings.AppSettings` and API request DTOs validate runtime-only fields such as `live_execution` and strategy configuration, while sharing `portfolio_risk` semantics with the typed YAML loader

Examples and operator artifacts include:

- `configs/base.yaml` for baseline typed YAML loading
- `configs/patterns/*.json` and `configs/strategies/*.json` for repository-backed pattern and strategy assets
- `examples/sample_backtest.yaml`, `examples/sample_backtest_krx.yaml`, and `examples/sample_live_kis.yaml` for operator reference

Notes:

- `configs/base.yaml` and `examples/sample_live_kis.yaml` now contain active typed examples for `portfolio_risk` and `app.reconciliation_interval`.
- Strategy/profile and pattern-set storage is file backed, not database backed.

## Test coverage snapshot

Coverage now spans the current operator-facing surface, not only the backtest core.

- Unit tests: config loading, app wiring, dashboard routes, live loop behavior, KIS integration, portfolio risk, reconciliation, repositories, analytics, and execution adapters
- Integration tests: backtest run API, pattern/strategy API flow, trade analytics API, config loader failures, and API security/validation

This gives a strong regression baseline for deterministic replay, runtime validation, dashboard control, and repository-backed pattern/strategy workflows.

## Remaining gaps before broader production use

1. **Distributed run execution**: backtests are separated through the internal dispatcher, but there is still no external queue or multi-worker model for long-running workloads.
2. **Session history UX**: recent live runtime sessions are visible in the dashboard, but long-term search and export are not yet implemented.
3. **Config parity**: strategy selection and some runtime-only fields are still not fully represented in the typed YAML loader.
4. **Exchange snapshot integration**: generic reconciliation exists and KIS balance snapshots are wired, but pending-order authority still depends on balance-snapshot signals rather than a dedicated unresolved-order API.
5. **Operational hardening**: repository-managed API keys now track disabled/last-used state, but richer auth, alerting, audit export, and deployment guidance are still lighter than a fully managed trading platform would require.

## Recommended next backlog

1. Add an external queue/worker model and clearer operator visibility around long-running backtests.
2. Add long-term search/export for live runtime session history and historical incident review.
3. Improve broker integrations, especially KIS, to expose a stronger unresolved/open-order source for reconciliation.
4. Decide whether additional strategy runtime settings should become first-class YAML fields or remain API/runtime-only inputs.
