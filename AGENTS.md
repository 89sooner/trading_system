# AGENTS.md

This repository is a Python trading-system workspace.

## Working defaults

- Use Python 3.12.
- Keep application code under `src/trading_system/`.
- Keep tests under `tests/`.
- Prefer small, explicit modules over large utility files.
- Preserve deterministic behavior in backtest code. Any time-dependent logic must be injected or configurable.
- Treat strategy, risk, execution, and analytics as separate layers. Do not couple them directly when an interface will do.
- When changing trading logic, update or add tests in the same change.
- When changing configuration shape, update `configs/`, `examples/`, and `README.md` together.

## Expected workflow

1. Read the nearest `AGENTS.md` if one exists.
2. Inspect the impacted package before editing.
3. Make the smallest coherent change that satisfies the task.
4. Run targeted tests first, then broader checks if the surface area is large.
5. Summarize changed files, risks, and follow-up work.

## Code style

- Prefer dataclasses, typed protocols, and small service objects.
- Keep side effects at boundaries such as providers, brokers, and file I/O.
- Avoid hidden state in strategy logic.
- Prefer composition over inheritance except for clearly defined base interfaces.
- Do not introduce new dependencies unless they clearly reduce complexity.

## Testing expectations

- Unit tests for risk rules, sizing, metrics, and strategy signal logic.
- Integration tests for order flow, broker adapters, and backtest orchestration when those layers are added.
- For bug fixes, add a regression test that fails before the fix and passes after it.

## Skills in this repo

Use repository skills from `.codex/skills/` or `.opencode/skills/` when the task matches their purpose.

- `feature-planner`: turn a request into a concrete implementation plan.
- `python-implementer`: implement or refactor Python code safely.
- `strategy-reviewer`: review strategy, backtest, and risk changes.
- `docs-maintainer`: update documentation, examples, and operator notes.
