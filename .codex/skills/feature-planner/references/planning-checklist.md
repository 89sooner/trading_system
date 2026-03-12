# Planning checklist

Use this checklist when turning a request into a plan.

## Domain concerns

- Does it affect signal generation, execution timing, or portfolio state?
- Does it change any risk limit or default sizing behavior?
- Could it produce different backtest and live behavior?
- Does it need deterministic clocks, fixtures, or seeded data?

## File-scope concerns

- `src/trading_system/strategy/` for signal logic
- `src/trading_system/risk/` for pre-trade checks and caps
- `src/trading_system/execution/` for order submission and broker boundaries
- `src/trading_system/portfolio/` for cash and position state
- `src/trading_system/backtest/` for orchestration and simulation
- `tests/` for unit and regression coverage
- `docs/` and `README.md` when behavior or usage changes
