# Architecture overview

The starter architecture is intentionally split into explicit layers and operator-facing surfaces.

- `app`: CLI entrypoint, service wiring, and live loop runtime
- `api`: HTTP routes, dashboard attachment, and security middleware
- `patterns`: pattern training, matching, alerts, and repositories
- `data`: market data models and provider interfaces
- `strategy`: signal generation and strategy contracts
- `risk`: position and order checks
- `execution`: order requests and broker interfaces
- `portfolio`: holdings, cash state, and persistence repository
- `backtest`: orchestration over historical data
- `analytics`: performance metrics and reporting helpers
- `integrations`: external clients such as KIS

Suggested flow:

1. A data provider yields bars, ticks, or snapshots.
2. A strategy produces a desired action.
3. Risk management validates the action.
4. Execution converts the action into an order request.
5. Portfolio state is updated from fills and optionally persisted to disk.
6. Analytics computes metrics from the event stream.

Current implementation note:

- The repository orchestrates both deterministic backtests and continuous live trading loops through a unified execution core (`execute_trading_step`).
- HTTP APIs expose backtests, pattern/strategy management, analytics, and dashboard control on top of the same runtime services.
- Live trading is managed by `LiveTradingLoop` with state control (`AppRunnerState`), heartbeat logging, and graceful shutdown.
- Portfolio manages local persistence (`book.json`) for seamless restart-safe operations across live sessions.
