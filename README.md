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
  patterns/
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

### One-command local run

If you want to run immediately without manually creating a venv or exporting variables:

```bash
./scripts/run_engine.sh backtest
./scripts/run_engine.sh live-preflight
```

- The script auto-creates `.venv` (if missing), installs dependencies, and runs the CLI.
- `live-preflight` uses `TRADING_SYSTEM_API_KEY` from your environment when present; otherwise it injects a local dummy key for preflight only.

This repository currently provides a clean package skeleton, a small risk-rule example, a deterministic single-symbol backtest loop, a chart-pattern learning and matching scaffold, and repository-level skills for planning, implementation, review, and documentation work.

- Fast smoke set: `pytest -m smoke -q`
- Extended set: `pytest -m "not smoke" -q`

### Backtest mode

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
python -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

### Backtest mode (KRX CSV example)

```bash
mkdir -p data/market
cat > data/market/005930.csv <<'CSV'
timestamp,open,high,low,close,volume
2024-01-02T00:00:00+00:00,70000,70500,69900,70400,1000
2024-01-03T00:00:00+00:00,70400,71000,70300,70900,1200
CSV

PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_CSV_DIR=data/market \
python -m trading_system.app.main --mode backtest --provider csv --symbols 005930 --trade-quantity 1
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
- `TRADING_SYSTEM_CSV_DIR` (optional): directory for CSV backtest files when `--provider csv` is used (default: `data/market`).

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
- KRX CSV verification loop note: `docs/runbooks/krx-csv-verification-loop.md`

## Operations baseline

- a built-in stateful `MomentumStrategy`
- close-price immediate fills
- fee-aware cash updates
- a printed equity curve and return summary

## Pattern-learning scaffold

The repository now includes a minimal chart-pattern pipeline for:

- storing labeled bar windows as training examples
- learning per-label pattern prototypes from those examples
- scoring the current bar window against learned patterns
- emitting alerts or converting matches into strategy signals

Run the example matcher with:

```bash
PYTHONPATH=src python -m trading_system.patterns.example
```
