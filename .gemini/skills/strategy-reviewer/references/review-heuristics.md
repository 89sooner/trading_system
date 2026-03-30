# Review heuristics

## Trading-specific failure patterns

- Buy and sell sign inversion
- Price and quantity unit mismatch
- Position limit checked before but not after aggregation
- Notional check using stale price
- Backtest fill assumptions that do not match execution semantics
- Portfolio cash updated without fee handling
- Strategy state derived from wall-clock time instead of injected event time

## Good review targets

- Limit validation paths
- Order request construction
- Fill application and portfolio updates
- Metric calculations that can divide by zero or mask loss states
