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

### Backtest mode

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
python -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

### Live preflight mode (no order submission)

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
python -m trading_system.app.main --mode live --symbols BTCUSDT
```

The built-in smoke backtest module is still available and routes through the app layer:

```bash
PYTHONPATH=src python -m trading_system.backtest.example
```

## Required environment variables

- `TRADING_SYSTEM_ENV`: logical runtime environment name (for example `local`, `staging`, `prod`).
- `TRADING_SYSTEM_TIMEZONE`: operator timezone used for runtime context (for example `Asia/Seoul`).
- `TRADING_SYSTEM_API_KEY`: live adapter credential injected from environment/secret manager only.

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

## Analysis docs

- Architecture overview: `docs/architecture/overview.md`
- Current workspace analysis: `docs/architecture/workspace-analysis.md`
- Incident runbook: `docs/runbooks/incident-response.md`
- Release gates: `docs/runbooks/release-gate-checklist.md`

## Operations baseline

- Boundary layers (`app`, `data`, `execution`) emit structured logs with a propagated `correlation_id`.
- Key events use fixed schema names: `order.created`, `order.rejected`, `order.filled`, `risk.rejected`, `exception`.
- Retry/timeout/circuit-breaker policies are applied only at external I/O boundaries.
