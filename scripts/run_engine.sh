#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/run_engine.sh backtest
#   ./scripts/run_engine.sh live-preflight

MODE="${1:-backtest}"

if [[ "$MODE" != "backtest" && "$MODE" != "live-preflight" ]]; then
  echo "Usage: $0 [backtest|live-preflight]" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip >/dev/null
pip install -e .[dev] >/dev/null

export PYTHONPATH=src
export TRADING_SYSTEM_ENV="${TRADING_SYSTEM_ENV:-local}"
export TRADING_SYSTEM_TIMEZONE="${TRADING_SYSTEM_TIMEZONE:-Asia/Seoul}"

if [[ "$MODE" == "backtest" ]]; then
  exec python -m trading_system.app.main --mode backtest --symbols BTCUSDT
fi

# live-preflight mode
export TRADING_SYSTEM_API_KEY="${TRADING_SYSTEM_API_KEY:-local-preflight-dummy-key}"
exec python -m trading_system.app.main --mode live --symbols BTCUSDT
