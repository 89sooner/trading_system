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
