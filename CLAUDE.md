# CLAUDE.md

This repository uses `AGENTS.md` as the primary repo-wide instruction file.

## Read first

- Follow `@AGENTS.md` for working defaults, workflow, code style, testing expectations, and repo-local skills.
- Treat `AGENTS.md` as the source of truth when this file is less specific.

## Claude-specific note

- Use the local skill directories documented in `AGENTS.md` when a task matches their purpose.
- Pay special attention to repository planning, execution, and frontend skills such as `feature-planner`, `plan-mode-orchestrator`, `build-mode-executor`, `verify-loop-inspector`, `frontend-product-designer`, `phase-planner`, and `claude-code-session-handoff`.

## Working summary

- Python 3.12
- App code under `src/trading_system/`
- Tests under `tests/`
- Keep strategy, risk, execution, portfolio, and analytics concerns separated
- Preserve deterministic backtest behavior and unified execution via `step.py`
- When trading logic changes, update tests in the same change
- When configuration shape changes, update `configs/`, `examples/`, and `README.md` together

For full repository guidance, read `@AGENTS.md`.
