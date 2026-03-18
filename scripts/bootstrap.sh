#!/usr/bin/env bash
set -euo pipefail

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

"$UV_BIN" venv --python 3.12 --seed .venv
"$UV_BIN" pip install --python .venv/bin/python -e '.[dev]'
"$UV_BIN" run --python .venv/bin/python --no-sync pytest
