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

if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
elif [[ -x "$HOME/.local/bin/uv" ]]; then
  UV_BIN="$HOME/.local/bin/uv"
else
  echo "uv not found. Install uv first, then rerun this script." >&2
  exit 127
fi

export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"
SYNC_DEPS="${TRADING_SYSTEM_SYNC_DEPS:-0}"
CREATED_VENV=0

if [[ ! -d .venv ]]; then
  "$UV_BIN" venv --python 3.12 --seed .venv
  CREATED_VENV=1
fi

if [[ "$CREATED_VENV" -eq 1 || "$SYNC_DEPS" == "1" ]]; then
  "$UV_BIN" pip install --python .venv/bin/python -e '.[dev]' >/dev/null
fi

export TRADING_SYSTEM_ENV="${TRADING_SYSTEM_ENV:-local}"
export TRADING_SYSTEM_TIMEZONE="${TRADING_SYSTEM_TIMEZONE:-Asia/Seoul}"

if [[ "$MODE" == "backtest" ]]; then
  exec "$UV_BIN" run --python .venv/bin/python --no-sync -m trading_system.app.main --mode backtest --symbols BTCUSDT
fi

# live-preflight mode
export TRADING_SYSTEM_API_KEY="${TRADING_SYSTEM_API_KEY:-local-preflight-dummy-key}"
exec "$UV_BIN" run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT
