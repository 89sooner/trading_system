# Architecture overview

The starter architecture is intentionally split into explicit layers.

- `data`: market data models and provider interfaces
- `strategy`: signal generation and strategy contracts
- `risk`: position and order checks
- `execution`: order requests and broker interfaces
- `portfolio`: holdings and cash state
- `backtest`: orchestration over historical data
- `analytics`: performance metrics and reporting helpers

Suggested flow:

1. A data provider yields bars, ticks, or snapshots.
2. A strategy produces a desired action.
3. Risk management validates the action.
4. Execution converts the action into an order request.
5. Portfolio state is updated from fills.
6. Analytics computes metrics from the event stream.
