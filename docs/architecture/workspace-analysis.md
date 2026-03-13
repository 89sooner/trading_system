# Workspace Analysis

This document captures the current implementation state of the trading-system workspace as of March 13, 2026.

## Repository state

The repository is no longer only a scaffold. It now includes a deterministic end-to-end backtest path, a CLI app entrypoint, typed configuration loading with validation, and both unit/integration tests for core orchestration.

Implemented behavior today:

- `app.main` provides CLI entrypoints for `backtest` and a safe `live` preflight mode.
- `app.services` composes strategy, provider, risk, broker simulator, and portfolio services.
- `backtest.engine.run_backtest` orchestrates signal -> risk -> broker fill -> portfolio updates -> equity curve.
- `execution.adapters` maps strategy signals to order requests.
- `execution.broker` provides deterministic fill/fee/slippage policies and a resilient broker wrapper (retry/timeout/circuit-breaker).
- `config.settings.load_settings` loads YAML into typed settings with human-friendly validation errors.
- `core.ops` provides structured logging, redaction, correlation IDs, and reusable resilience helpers.

## Layer analysis

### App

The app layer now exists and separates CLI argument handling (`app.main`) from service wiring (`app.services`).

- `--mode backtest` executes the deterministic backtest path.
- `--mode live` currently performs preflight validation only (including required secret checks) and does not submit orders.

This keeps live mode safe while allowing operators to validate runtime inputs.

### Data

`MarketDataProvider` has an `InMemoryMarketDataProvider` implementation suitable for deterministic tests and smoke runs.

Current limitation:
- No external historical/live provider adapter is implemented yet.

### Strategy

`MomentumStrategy` provides a deterministic stateful example strategy based on consecutive closes.

Current limitation:
- No strategy registry/plugin mechanism yet; selection is currently fixed in service composition.

### Risk

`RiskLimits` enforces max order size, projected position, and projected notional checks.

Current limitation:
- Exposure semantics are still single-portfolio and simple (no gross/net portfolio-level policies).

### Execution

Execution now has explicit boundaries:

- signal-to-order adapter
- broker simulator interface
- policy-based fill/fee/slippage simulation
- resilience wrapper for external-I/O-like failure handling

Current limitation:
- No real broker adapter or persistent order lifecycle state machine yet.

### Portfolio

`PortfolioBook` supports cash/position updates with fee-aware fill application and deterministic behavior.

Current limitation:
- No average price, realized/unrealized PnL decomposition, or storage persistence yet.

### Backtest

Backtest orchestration is implemented and deterministic for identical inputs.

Current limitation:
- Multi-symbol portfolio accounting is supported for marking existing positions, but the default app path intentionally restricts runtime to one symbol for safety/simplicity.

### Analytics

`cumulative_return` is available and integrated into `BacktestResult.total_return`.

Current limitation:
- Drawdown/trade stats/turnover metrics are not yet part of the default report.

## Configuration and examples

Configuration shape is now aligned for executable baseline fields:

- `configs/base.yaml` includes `app`, `market_data`, `risk`, and `backtest` sections compatible with typed settings.
- `examples/sample_backtest.yaml` includes required risk/backtest fields and remains an operator-facing scenario reference.

Notes:
- The example still contains additional strategy metadata that is not yet consumed by the current CLI app composition.

## Test coverage snapshot

Coverage includes:

- Unit tests: strategy/risk/portfolio/analytics/config/app/execution adapters and broker behavior.
- Integration tests: orchestration happy path, deterministic replay, risk rejection, provider failure, broker failure/timeout paths, config loader invalid schema/type paths.

This gives a solid regression baseline for the current deterministic backtest architecture.

## Remaining gaps before true live execution

1. **Real adapters**: implement external market data and broker adapters behind existing protocols.
2. **Live orchestration**: add runtime loop, heartbeat, and durable state transitions for order lifecycle.
3. **Persistence/recovery**: add checkpointing/event storage for restart-safe operation.
4. **Operational gates**: formalize pre-production checks (runbook drills, key rotation, alert routing).
5. **Expanded analytics**: add drawdown and trade-level metrics for operational monitoring.

## Recommended next backlog

1. Introduce a real data-provider adapter with strict timeout/retry configuration.
2. Add a broker adapter contract test suite (happy path + failure path) using fakes.
3. Extend `live` mode from preflight to paper-trade loop with explicit dry-run guard.
4. Add release-gate documentation with pass/fail checklist before enabling live order submission.
