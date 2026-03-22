# Architecture overview

The starter architecture is intentionally split into explicit layers.

- `data`: market data models and provider interfaces
- `strategy`: signal generation and strategy contracts
- `risk`: position and order checks
- `execution`: order requests and broker interfaces
- `portfolio`: holdings, cash state, and persistence repository
- `backtest`: orchestration over historical data
- `analytics`: performance metrics and reporting helpers

Suggested flow:

1. A data provider yields bars, ticks, or snapshots.
2. A strategy produces a desired action.
3. Risk management validates the action.
4. Execution converts the action into an order request.
5. Portfolio state is updated from fills and optionally persisted to disk.
6. Analytics computes metrics from the event stream.

Current implementation note:

- The repository now includes a deterministic v1 backtest loop that evaluates bars sequentially, applies allowed signals at the current bar close, charges configured fees, and records an equity curve for analytics.
