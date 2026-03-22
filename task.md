# Phase 3 Task Breakdown

## Epic A — Live Dashboard API + Frontend
- [x] Add ring buffer + [recent_events()](file:///home/roqkf/trading_system/src/trading_system/core/ops.py#130-134) to [StructuredLogger](file:///home/roqkf/trading_system/src/trading_system/core/ops.py#106-158) in [core/ops.py](file:///home/roqkf/trading_system/src/trading_system/core/ops.py)
- [x] Create [api/routes/dashboard.py](file:///home/roqkf/trading_system/src/trading_system/api/routes/dashboard.py) (status, positions, events, control)
- [x] Add DTOs to [api/schemas.py](file:///home/roqkf/trading_system/src/trading_system/api/schemas.py)
- [x] Register dashboard router + thread-safe `app.state.loop` wiring in [api/server.py](file:///home/roqkf/trading_system/src/trading_system/api/server.py)
- [x] Create [frontend/dashboard.html](file:///home/roqkf/trading_system/frontend/dashboard.html)
- [x] Add nav link in [frontend/index.html](file:///home/roqkf/trading_system/frontend/index.html)
- [x] Write [tests/unit/test_dashboard_routes.py](file:///home/roqkf/trading_system/tests/unit/test_dashboard_routes.py)

## Epic B — Portfolio-Level Risk Guards
- [x] Create [risk/portfolio_limits.py](file:///home/roqkf/trading_system/src/trading_system/risk/portfolio_limits.py) with [PortfolioRiskLimits](file:///home/roqkf/trading_system/src/trading_system/risk/portfolio_limits.py#15-83)
- [x] Add `PortfolioRiskSettings` to config and app settings
- [x] Update [configs/base.yaml](file:///home/roqkf/trading_system/configs/base.yaml) + `examples/` + [README.md](file:///home/roqkf/trading_system/README.md)
- [x] Extend [TradingContext](file:///home/roqkf/trading_system/src/trading_system/execution/step.py#23-30) to carry `portfolio_risk`
- [x] Extend [step.py](file:///home/roqkf/trading_system/src/trading_system/execution/step.py) to check drawdown limit and SL/TP
- [x] Wire [PortfolioRiskLimits](file:///home/roqkf/trading_system/src/trading_system/risk/portfolio_limits.py#15-83) in [app/services.py](file:///home/roqkf/trading_system/src/trading_system/app/services.py)
- [x] Write [tests/unit/test_portfolio_risk_limits.py](file:///home/roqkf/trading_system/tests/unit/test_portfolio_risk_limits.py)
- [x] Write regression test: step skips when daily limit breached

## Epic C — Multi-Symbol Orchestration
- [ ] Update [app/loop.py](file:///home/roqkf/trading_system/src/trading_system/app/loop.py) [_run_tick](file:///home/roqkf/trading_system/src/trading_system/app/loop.py#104-122) for multi-symbol
- [ ] Update per-symbol timestamp tracking (`dict[str, datetime]`)
- [ ] Relax single-symbol guard in [app/services.py](file:///home/roqkf/trading_system/src/trading_system/app/services.py) for live mode
- [ ] Update strategy factory for multi-symbol strategy dispatch
- [ ] Write `tests/unit/test_live_loop_multi_symbol.py`

## Epic D — Trade-Level Analytics
- [ ] Create `analytics/trades.py` (`CompletedTrade`, `extract_trades`)
- [ ] Create `analytics/advanced_metrics.py` (profit_factor, sharpe, sortino, avg_win, avg_loss)
- [ ] Extend backtest API response with `TradeStatsDTO`
- [ ] Write `tests/unit/test_trades.py`
- [ ] Write `tests/unit/test_advanced_metrics.py`

## Epic E — Exchange Reconciliation (Phase 3.5)
- [ ] Create `execution/reconciliation.py`
- [ ] Add `get_account_balance()` to broker protocol + KIS adapter
- [ ] Wire reconciliation interval into [app/loop.py](file:///home/roqkf/trading_system/src/trading_system/app/loop.py)
- [ ] Write reconciliation tests

## Cross-cutting
- [ ] `uv run pytest` all green after each epic
- [ ] `ruff check` clean after each epic
- [ ] Update [README.md](file:///home/roqkf/trading_system/README.md) and [GEMINI.md](file:///home/roqkf/trading_system/GEMINI.md) after each epic merge
