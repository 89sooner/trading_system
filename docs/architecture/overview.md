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
- HTTP APIs expose backtests, pattern/strategy management, analytics, admin key management, `/health`, dashboard control, and searchable/exportable live runtime session history with session evidence on top of the same runtime services.
- Live trading is managed by `LiveTradingLoop` with state control (`AppRunnerState`), heartbeat logging, and graceful shutdown.
- Portfolio state persists locally via `book.json`, while backtest runs, run metadata, dashboard equity history, live runtime session history, and incident-relevant runtime event archives persist through file-based storage or Supabase-backed PostgreSQL depending on `DATABASE_URL`.
- Backtest runs carry operator metadata such as provider, broker, strategy profile, pattern set, source, and optional notes.
- Backtest execution is owned by an API dispatcher with `queued`/`running`/terminal states, and dispatcher status plus queue depth are queryable through the API.
- Order creation, fills, rejections, and risk rejections can be stored, queried, and exported as durable order audit records owned by a backtest run or live session. Broker order ids are preserved when available.
- KIS reconciliation uses open-order snapshots as the preferred pending-order authority and falls back to balance-snapshot pending signals only when the capability is unavailable.
- Repository-managed API keys expose governance fields such as disabled state and last-used tracking.
- Webhook notifications provide bounded fire-and-forget outbound delivery for selected runtime events.
