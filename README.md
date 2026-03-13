# trading_system

Starter scaffold for a modular Python trading system.

## Goals

- Separate market data, strategy, risk, execution, portfolio, backtest, and analytics concerns.
- Keep domain logic testable without live infrastructure.
- Make it easy to grow from local research to a more production-like service layout.

## Repository layout

```text
src/trading_system/
  analytics/
  app/
  backtest/
  config/
  core/
  data/
  execution/
  portfolio/
  risk/
  strategy/

tests/
docs/
configs/
examples/
.codex/skills/
.opencode/skills/
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Run commands

### Test suites (CI split)

- Fast smoke set: `pytest -m smoke -q`
- Extended set: `pytest -m "not smoke" -q`

The smoke set is intended for quick CI feedback. The extended set covers broader integration and failure-path scenarios.


Backtest mode:

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
python -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

Operational (live placeholder) mode validation:

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
python -m trading_system.app.main --mode live --symbols BTCUSDT
```

The built-in smoke backtest module is still available and now routes through the app layer:

```bash
PYTHONPATH=src python -m trading_system.backtest.example
```

## Required environment variables

- `TRADING_SYSTEM_ENV`: logical runtime environment name (for example `local`, `staging`, `prod`).
- `TRADING_SYSTEM_TIMEZONE`: operator timezone used for runtime context (for example `Asia/Seoul`).

- `TRADING_SYSTEM_API_KEY`: live execution adapter credential injected from environment/secret manager only.


## Configuration schema

`src/trading_system/config/settings.py` provides a YAML loader with validation:

```python
from trading_system.config import load_settings

settings = load_settings("configs/base.yaml")
```

Required top-level sections:

- `app`: `environment` (str), `timezone` (str), `mode` (`backtest`|`live`)
- `market_data`: `provider` (str), `symbols` (list[str])
- `risk`: `max_position`, `max_notional`, `max_order_size` (Decimal, > 0)
- `backtest`: `starting_cash` (> 0), `fee_bps` (0~1000), `trade_quantity` (> 0)

All amount/quantity/fee fields are parsed as `Decimal`. Validation errors return human-friendly messages for missing keys, invalid types, and out-of-range values.

## Current status

This repository currently provides a clean package skeleton, a small risk-rule example, a deterministic single-symbol backtest loop, and repository-level skills for planning, implementation, review, and documentation work.

## Analysis docs

- Architecture overview: `docs/architecture/overview.md`
- Current workspace analysis: `docs/architecture/workspace-analysis.md`

## Try a simple example

The repository includes a deterministic smoke example:

```bash
PYTHONPATH=src python -m trading_system.backtest.example
```

It runs a small single-symbol bar sequence through the v1 backtest loop with:

- a built-in stateful `MomentumStrategy`
- close-price immediate fills
- fee-aware cash updates
- a printed equity curve and return summary


## Operations baseline

- Boundary layers (`app`, `data`, `execution`) emit structured logs with a propagated `correlation_id`.
- Key events use fixed schema names: `order.created`, `order.rejected`, `order.filled`, `risk.rejected`, `exception`.
- Retry/timeout/circuit-breaker policies are applied only at external I/O boundaries.
- Runbook for outage response: `docs/runbooks/incident-response.md`.
