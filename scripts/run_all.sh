#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/run_all.sh              # Start both backend API + frontend dev server
#   ./scripts/run_all.sh --backend    # Start backend API only
#   ./scripts/run_all.sh --frontend   # Start frontend dev server only
#
# Environment variables:
#   API_PORT              Backend port (default: 8000)
#   FRONTEND_PORT         Frontend port (default: 3000)
#   TRADING_SYSTEM_SYNC_DEPS  Set to 1 to force Python dependency resync

MODE="${1:-all}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PIDS=()

cleanup() {
  echo ""
  echo "Shutting down..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  echo "All processes stopped."
}
trap cleanup EXIT INT TERM

# ---------- Backend setup ----------

start_backend() {
  local api_port="${API_PORT:-8000}"

  if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
  elif [[ -x "$HOME/.local/bin/uv" ]]; then
    UV_BIN="$HOME/.local/bin/uv"
  else
    echo "[backend] uv not found. Install uv first." >&2
    exit 127
  fi

  export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"
  SYNC_DEPS="${TRADING_SYSTEM_SYNC_DEPS:-0}"
  CREATED_VENV=0

  if [[ ! -d .venv ]]; then
    echo "[backend] Creating virtualenv..."
    "$UV_BIN" venv --python 3.12 --seed .venv
    CREATED_VENV=1
  fi

  if [[ "$CREATED_VENV" -eq 1 || "$SYNC_DEPS" == "1" ]]; then
    echo "[backend] Installing Python dependencies..."
    "$UV_BIN" pip install --python .venv/bin/python -e '.[dev]' >/dev/null
  fi

  export TRADING_SYSTEM_ENV="${TRADING_SYSTEM_ENV:-local}"
  export TRADING_SYSTEM_TIMEZONE="${TRADING_SYSTEM_TIMEZONE:-Asia/Seoul}"

  echo "[backend] Starting API server on port ${api_port}..."
  "$UV_BIN" run --python .venv/bin/python --no-sync \
    -m uvicorn trading_system.api.server:create_app \
    --factory --host 0.0.0.0 --port "$api_port" &
  PIDS+=($!)
}

# ---------- Frontend setup ----------

start_frontend() {
  local frontend_port="${FRONTEND_PORT:-3000}"
  local frontend_dir="$ROOT_DIR/frontend"

  if [[ ! -d "$frontend_dir" ]]; then
    echo "[frontend] frontend/ directory not found." >&2
    exit 1
  fi

  if ! command -v node >/dev/null 2>&1; then
    echo "[frontend] node not found. Install Node.js first." >&2
    exit 127
  fi

  if [[ ! -d "$frontend_dir/node_modules" ]]; then
    echo "[frontend] Installing npm dependencies..."
    (cd "$frontend_dir" && npm install)
  fi

  if [[ ! -f "$frontend_dir/.env.local" ]]; then
    if [[ -f "$frontend_dir/.env.local.example" ]]; then
      echo "[frontend] Creating .env.local from .env.local.example..."
      cp "$frontend_dir/.env.local.example" "$frontend_dir/.env.local"
    fi
  fi

  echo "[frontend] Starting Next.js dev server on port ${frontend_port}..."
  (cd "$frontend_dir" && PORT="$frontend_port" npm run dev) &
  PIDS+=($!)
}

# ---------- Main ----------

case "$MODE" in
  --backend)
    start_backend
    ;;
  --frontend)
    start_frontend
    ;;
  all|--all)
    start_backend
    start_frontend
    ;;
  *)
    echo "Usage: $0 [all|--all|--backend|--frontend]" >&2
    exit 2
    ;;
esac

echo ""
echo "=== Services running ==="
if [[ "$MODE" != "--frontend" ]]; then
  echo "  Backend API : http://localhost:${API_PORT:-8000}"
fi
if [[ "$MODE" != "--backend" ]]; then
  echo "  Frontend    : http://localhost:${FRONTEND_PORT:-3000}"
fi
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

wait
